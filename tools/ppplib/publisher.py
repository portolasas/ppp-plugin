"""The publisher by package (entwurf/ERWEITERUNGEN.md, A; VERBUNDEN VB-19): the lines on the publisher after ppp connect,
and ppp import --create, which builds an empty first solution with the publisher of the settings and imports it.

ppp never changes a publisher: an import creates one only where it is missing and no other publisher has its prefix,
never in the default environment (there a card creates it in the portal). Whether the server takes the empty package
built from the plugin's template as it took the one of the pac test (N8: the head of an export of the same environment)
is not proven yet (A.6); the check after the import reads solution and publisher again and names every difference as a
WARNING line, so nothing deviates silently."""
from __future__ import annotations

import json
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from . import agent, cards, connected, importlog, solution, tenant
from .project import ToolError, load_config
from .tenant import TenantError

EMPTY_PARTS = {"flows": {}, "refs": [], "apps": []}     # an empty solution: no flows, references or apps
ENTRIES = {"[content_types].xml", "solution.xml", "customizations.xml"}
CARD = ("Solutions › New solution › Publisher › New publisher, with the four values of ppp settings")
FIELDS = ("uniqueName", "displayName", "prefix", "optionValuePrefix")


def _settings_publisher() -> dict | None:
    return agent.publisher_of(agent.read_settings())


def _default(env: dict) -> bool:
    """The environment is the default environment, whose name the plugin knows (connected.DEFAULT_ENVIRONMENT)."""
    return str(env.get("name") or "").strip().lower() == connected.DEFAULT_ENVIRONMENT.lower()


def _shown(field: str, value) -> str:
    return f'"{value}"' if field == "displayName" else str(value)


def _differences(online: dict, wanted: dict) -> list[str]:
    """The values of the publisher online that are not those of the settings, as "<field> <online> vs <settings>". The
    prefix counts in lower case (the server keeps it so), every other value as it is."""
    same = lambda field: (str(online.get(field) or "").lower() == str(wanted[field]).lower() if field == "prefix"
                          else online.get(field) == wanted[field])
    return [f"{f} {_shown(f, online.get(f))} vs {_shown(f, wanted[f])}" for f in FIELDS if not same(f)]


# ------------------------------------------------------------------ ppp connect
def connect_lines(root: Path, env: dict) -> list[str]:
    """The lines on the publisher of the settings in the environment `env` (tenant.environment), printed by ppp connect
    after connected.connect (ERWEITERUNGEN A.1): as in the settings, MISSING, or WARNING lines. Never raises: the
    connection is written already, so a failed read gives a line instead of an error."""
    wanted = _settings_publisher()
    if not wanted:
        return ["Publisher: not set (ppp settings --publisher-name …)."]
    name, alias = wanted["uniqueName"], env.get("alias", "?")
    try:
        found = tenant.publisher(env["url"], name, wanted["prefix"], wanted["optionValuePrefix"])
    except Exception as ex:     # noqa: BLE001 - ppp connect has written the connection already
        return [f"Publisher {name}: not read in {alias} ({str(ex).splitlines()[0][:200]}); ppp connect again reads it."]
    lines = []
    if found["found"] is None:
        if _default(env):
            lines.append(f"MISSING Publisher {name} in {alias}: a card creates it in the portal ({CARD}).")
        elif env.get("role") == "production":
            lines.append(f"MISSING Publisher {name} in {alias}: role production, ppp import does not import there.")
        else:
            lines.append(f"MISSING Publisher {name} in {alias}: ppp import --create builds the first solution with it.")
    else:
        different = _differences(found["found"], wanted)
        lines.append(f"WARNING Publisher {name} in {alias} differs from the settings: " + "; ".join(different)
                     + ". ppp never changes a publisher." if different else f"Publisher {name}: as in the settings.")
    if found["prefix_others"]:
        lines.append(f"WARNING prefix {wanted['prefix'].lower()} belongs to the publisher {', '.join(found['prefix_others'])} in {alias}.")
    if found["option_others"]:
        lines.append(f"WARNING option value prefix {wanted['optionValuePrefix']} is used by the publisher "
                     f"{', '.join(found['option_others'])} in {alias}.")
    return lines


# ------------------------------------------------------------------ ppp import --create
def _empty_ok(package: Path, name: str, publisher: dict) -> str | None:
    """The built ZIP itself, not what it was built from (ERWEITERUNGEN A.2, point 6): exactly the three files, the
    manifest of an unmanaged solution `name` 1.0.0.1, no RootComponent, the four values of `publisher`, customizations.xml
    byte for byte the template's. None when all holds, else what does not."""
    try:
        with zipfile.ZipFile(package) as z:
            names = z.namelist()
            found = {n.lower(): n for n in names}
            if len(names) != len(ENTRIES) or set(found) != ENTRIES:
                return "it holds " + ", ".join(sorted(names)) + ", not exactly [Content_Types].xml, solution.xml and customizations.xml"
            xml, custom = z.read(found["solution.xml"]), z.read(found["customizations.xml"])
    except (OSError, zipfile.BadZipFile) as ex:
        return f"it cannot be read ({ex})"
    info = solution.manifest(xml)
    if info["uniqueName"] != name or info["version"] != solution.EMPTY_VERSION or b"<Managed>0</Managed>" not in xml:
        return (f"its manifest names {info['uniqueName'] or '?'} {info['version'] or '?'}" + (", managed" if info["managed"] else "")
                + f", not the unmanaged {name} {solution.EMPTY_VERSION}")
    if re.search(rb"<RootComponent[\s/>]", xml):
        return "solution.xml has a RootComponent"
    packed = solution.publisher_of(xml)
    if packed is None:
        return "solution.xml has no publisher"
    different = [f"{f} {_shown(f, packed[f])}, the settings {_shown(f, publisher[f])}" for f in FIELDS if packed[f] != publisher[f]]
    if different:
        return "its publisher has " + "; ".join(different)
    if custom != (solution.EMPTY_TEMPLATE / "Other" / "Customizations.xml").read_bytes():
        return "customizations.xml is not the one of the template"
    return None


def _check_publisher(env: dict, wanted: dict) -> tuple[bool, list[str]]:
    """Point 5 of A.2: whether the import creates the publisher (True) or finds it with the same four values (False), and
    the WARNING lines that go with it; a ToolError for every case in which the import is refused."""
    name, alias = wanted["uniqueName"], env["alias"]
    found = tenant.publisher(env["url"], name, wanted["prefix"], wanted["optionValuePrefix"])
    if found["found"] is None and _default(env):
        raise ToolError(f"The publisher {name} is missing in {alias}, the default environment: a card creates it in the portal "
                        f"({CARD}); then ppp import --create again.")
    if found["found"] is not None:
        different = _differences(found["found"], wanted)
        if different:
            raise ToolError(f"The publisher {name} in {alias} differs from the settings: " + "; ".join(different)
                            + ". ppp never changes a publisher: align the settings with it (ppp settings --publisher-from <an "
                              "unpacked solution of it>) or choose another publisher.")
    if found["prefix_others"]:
        raise ToolError(f"The prefix {wanted['prefix'].lower()} belongs to the publisher {', '.join(found['prefix_others'])} in "
                        f"{alias}: the import would not create {name} with it. ppp never changes a publisher; choose another "
                        "prefix (ppp settings --publisher-prefix) or that publisher.")
    warnings = [f"WARNING option value prefix {wanted['optionValuePrefix']} is used by the publisher "
                f"{', '.join(found['option_others'])} in {alias}."] if found["option_others"] else []
    return found["found"] is None, warnings


def _new_transfer(config: dict, name: str | None) -> bool:
    """--transfer: whether project.json gets name as the solution of role transfer (True), or has it so already (False).
    Only in mode large, without another transfer solution, never for the main solution; a ToolError otherwise."""
    if not name:
        raise ToolError("--transfer needs --solution <UniqueName>: the name of the transfer solution to create.")
    if not (isinstance(name, str) and solution.EMPTY_NAME.fullmatch(name)):
        raise ToolError(f"{name!r} is not the unique name of a solution: letters, digits and underscores, no digit first.")
    entries = [s for s in config.get("solutions") or [] if isinstance(s, dict) and s.get("uniqueName")]
    entry = next((s for s in entries if str(s["uniqueName"]).lower() == name.lower()), None)
    if entry and entry.get("role") == "transfer":
        return False
    if config.get("mode") != "large":
        raise ToolError(f"--transfer needs mode large in project.json (it is {config.get('mode') or 'not set'}): only a project in "
                        "mode large packs a transfer solution.")
    if entry and entry.get("role") == "main":
        raise ToolError(f"{entry['uniqueName']} is the main solution in project.json: the transfer solution is a second one.")
    if entry:
        raise ToolError(f"{entry['uniqueName']} has the role {entry.get('role')} in project.json: --transfer adds a solution that "
                        "is not there yet.")
    other = next((s for s in entries if s.get("role") == "transfer"), None)
    if other:
        raise ToolError(f"project.json names {other['uniqueName']} as the transfer solution already: a project has one.")
    return True


def _add_transfer(root: Path, name: str) -> str:
    """Write name into project.json › solutions with the role transfer, in the form ppp unpack writes a solution there
    (structure.register_solution); returns the line that names the change."""
    path = root / "project.json"
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    config.setdefault("solutions", []).append({"uniqueName": name, "role": "transfer"})
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return f"project.json: {name} added as the transfer solution; commit it with the export."


def _solution_of(config: dict, name: str | None) -> str:
    """The solution to create: name (of role main or transfer in project.json), else the main solution."""
    entries = [s for s in config.get("solutions") or [] if isinstance(s, dict) and s.get("uniqueName")]
    if name is None:
        main = next((s for s in entries if s.get("role") == "main"), None)
        if not main:
            raise ToolError("project.json names no main solution: ppp import --create --solution <UniqueName> names one of role "
                            "main or transfer.")
        return str(main["uniqueName"])
    entry = next((s for s in entries if str(s["uniqueName"]).lower() == name.lower()), None)
    if not entry:
        raise ToolError(f"{name} is not in project.json › solutions: ppp import --create creates a solution the project names, "
                        "of role main or transfer.")
    if entry.get("role") not in ("main", "transfer"):
        raise ToolError(f"{entry['uniqueName']} has the role {entry.get('role')} in project.json: ppp import --create creates a "
                        "solution of role main or transfer.")
    return str(entry["uniqueName"])


def _build(root: Path, env: dict, name: str, wanted: dict) -> Path:
    """The empty package in exchange/tenant/<Name>/create_1.0.0.1.zip, packed by pac from the template; one built by an
    earlier call that never reached the server is replaced."""
    path = connected.backup_folder(root, env, name) / f"create_{solution.EMPTY_VERSION}.zip"
    path.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="ppp-create-") as tmp:
        folder = Path(tmp) / name
        solution.empty_solution(folder, name, wanted)
        solution.pack(folder, path)
    wrong = _empty_ok(path, name, wanted)
    if wrong:
        raise ToolError(f"The package {path.name} built for {name} is not an empty solution with the publisher of the settings: "
                        f"{wrong}. Nothing was imported.")
    return path


def create(root: Path, name: str | None, confirmed: bool, wait: float, transfer: bool = False) -> int:
    """ppp import --create [--solution <name> [--transfer]] [--confirmed] [--wait <s>] (ERWEITERUNGEN A.1, A.2, A.5): an
    empty solution with the publisher of the settings, imported into the project's environment after the checks of A.2,
    always after a card (CONFIRM FIRST). name: a solution of role main or transfer in project.json; None: the main
    solution. transfer: name may be missing in project.json; in mode large without a transfer solution it is written there
    with the role transfer, only on the call with confirmed, right before the import starts (_new_transfer). The entry in
    imports.jsonl has "kind": "create" and the fields connected.report_imported reads for it (A.4). A create under way (an entry
    started) is waited for, never started twice."""
    called = datetime.now().isoformat(timespec="seconds")
    env = tenant.environment(root)
    connected.need_role(env)                                        # 1
    if env["role"] == "production":
        raise ToolError(f"{env['alias']} has the role production: ppp import does not import there.")
    config = load_config(root)
    adding = _new_transfer(config, name) if transfer else False
    if adding:
        config = {**config, "solutions": [*(config.get("solutions") or []), {"uniqueName": name, "role": "transfer"}]}
    name = _solution_of(config, name)                                # 2
    last = next((e for e in reversed(importlog.entries(root)) if e.get("kind") == "create" and importlog.of(e, name, env["alias"])), None)
    if last and last.get("status") == "started":
        return connected.follow_import(root, env, last, EMPTY_PARTS, wait, resumed=True)
    if (root / "solution" / name).exists():
        raise ToolError(f"solution/{name}/ exists already: a solution with an export in the project is created already.")
    wanted = _settings_publisher()                                   # 3
    if not wanted:
        raise ToolError("Publisher: not set (ppp settings --publisher-name …); ppp import --create builds the solution with it.")
    named = config.get("publisher") if isinstance(config.get("publisher"), str) else None
    if not named or named.lower() != wanted["uniqueName"].lower():
        raise ToolError(f"project.json names the publisher {named or '(none)'}, the settings {wanted['uniqueName']}: ppp check names "
                        "what to align.")
    online = tenant.solutions(env["url"]).get(name.lower())          # 4
    if online:
        raise ToolError(f"{online['name']} is in {env['alias']} already ({online['version']}): nothing to create; ppp export "
                        f"--solution {online['name']}.")
    running = tenant.running_imports(env["url"], name)
    if running:
        raise TenantError("BUSY", f"an import of {name} is running in {env['alias']} (progress {running[0]} %). Wait for it; "
                                  "ppp tenant shows where it stands.")
    new, warnings = _check_publisher(env, wanted)                    # 5
    path = _build(root, env, name, wanted)                           # 6
    digest = solution.sha256(path)
    card = (f"CONFIRM FIRST (a new solution with its publisher): show a tenant-step card with the environment {env['name']} "
              f"(role {env['role']}), the solution {name} {solution.EMPTY_VERSION}, empty (package {path.name}; its SHA-256 "
              f"stands in the entry: the package is built anew with --confirmed), the publisher {wanted['uniqueName']} (display name \"{wanted['displayName']}\", prefix "
              f"{wanted['prefix']}, option value prefix {wanted['optionValuePrefix']}), "
              + ("created by this import" if new else f"in {env['alias']} already and used as it is")
              + ", that " + ("both stay" if new else "the solution stays") + " in the tenant until the user deletes "
              + ("them by hand: first the solution, then the publisher" if new else "it by hand")
              + (f"; project.json gets {name} as the transfer solution" if adding else "")
              + "; and the answers \"Create\" and \"Not now\". After \"Create\": the same command with --confirmed.")
    if not cards.confirm(card, confirmed):       # always, whatever confirmImport says (A.5)
        for line in warnings:
            print(line)
        return 1
    if adding:      # only now, right before the start: the card changed nothing in the project
        print(_add_transfer(root, name))
    entry = importlog.record(root, {"solution": name, "version": solution.EMPTY_VERSION, "zip": path.name, "sha": digest,
                                     "environment": env["alias"], "status": "started", "kind": "create", "called": called,
                                     "publisher": wanted["uniqueName"], "publisher_new": new, "publisher_values": wanted,
                                     "online_before": None, "flows_before": {}, "jobs_before": tenant.import_jobs(env["url"], name)})
    result = connected.hand_over(root, env, entry, path, wait)
    if result["state"] == "skipped":
        try:        # records the entry as not_started and raises
            connected.report_failed(root, env, entry, f"SKIPPED: {result['message']}", result=result)
        except ToolError:       # its message names ppp pack --version, which a create does not take
            raise ToolError(f"pac skipped the import of {path.name}: {name} came into {env['alias']} meanwhile ({result['message']}). "
                            f"Nothing was imported; ppp export --solution {name} takes it into the project.") from None
    if result["state"] == "failed":
        return connected.report_failed(root, env, entry, f"{result.get('kind', 'FAILED')}: {result['message']}", result=result)
    return connected.follow_import(root, env, entry, EMPTY_PARTS, max(wait - result["seconds"], 0), resumed=False)


def after_import(root: Path, env: dict, entry: dict) -> list[str]:
    """The hook of connected.report_imported for an entry of kind create, after its line CREATED (ERWEITERUNGEN A.1): read the
    solution and the publisher once more and return the WARNING lines when something differs (the solution belongs to
    another publisher, a value of the publisher differs from the settings); no line when all is as in the settings.
    Each line that starts with WARNING counts among ppp's warnings of the import. The values are those the package was
    built with (publisher_values in the entry), else those of the settings now. A failed read is a WARNING line too:
    the import is in, its record must still be written."""
    name = entry["solution"]
    wanted = entry.get("publisher_values") if isinstance(entry.get("publisher_values"), dict) else _settings_publisher()
    wanted = wanted or {"uniqueName": entry.get("publisher", "?")}
    lines = []
    try:
        online = tenant.solutions(env["url"]).get(name.lower()) or {}
        owner = str(online.get("publisher") or "")
        if owner.lower() != str(wanted["uniqueName"]).lower():
            lines.append(f"WARNING {name} belongs to the publisher {owner or '(none named)'}")
        if all(f in wanted for f in FIELDS):
            found = tenant.publisher(env["url"], wanted["uniqueName"], wanted["prefix"], wanted["optionValuePrefix"])["found"]
            if found is None:
                lines.append(f"WARNING the publisher {wanted['uniqueName']} is not in {env['alias']} after the import")
            else:
                same = lambda f: (str(found.get(f) or "").lower() == str(wanted[f]).lower() if f == "prefix" else found.get(f) == wanted[f])
                lines += [f"WARNING the publisher in {env['alias']} has {f} {_shown(f, found.get(f))}, the settings "
                          f"{_shown(f, wanted[f])}" for f in FIELDS if not same(f)]
    except (ToolError, OSError, KeyError, ValueError) as ex:
        lines.append(f"WARNING the check after the import could not read the tenant ({str(ex).splitlines()[0][:200]}); ppp tenant "
                     "and ppp connect show the state")
    return lines
