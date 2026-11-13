"""The members of the transfer solution (entwurf/ERWEITERUNGEN.md, B; VERBUNDEN VB-13): ppp members lists them, and
with names adds flows, environment variables and connection references of the main solution to it, each at its ID
through tenant.add_member, a flow with the references and variables it uses.

The names come from the committed folder solution/<main>/, the IDs from there (a flow's, in its file name) or from the
tenant (a variable's and a reference's, one row each); every check comes before the first call, and whether a component
is a member afterwards says tenant.members, not the exit code of pac."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import connected, gitutil, tenant
from .project import ToolError, load_config, solution_with_role
from .tenant import TenantError

SHOWN = 8       # candidates named in a message about an unknown name
FLOW_FILE = re.compile(r"(.+)-(" + tenant.GUID.pattern + r")\.json")
REFERENCE_NAME = re.compile(r'connectionreferencelogicalname="([^"]+)"', re.I)
# Kinds of a solution's root components that ppp does not add, as Solution.xml names them by type code: the kind in words
OTHER_KINDS = {"1": "table", "2": "column", "9": "option set", "20": "security role", "26": "view", "29": "flow", "60": "form",
               "61": "web resource", "62": "site map", "66": "custom control", "300": "canvas app", "371": "connector",
               "372": "connector", "380": "environment variable", "381": "environment variable value", "400": "AI model",
               "401": "AI model", "10026": "model-driven app"}


# ------------------------------------------------------------------ what the main solution holds
def _components(folder: Path) -> dict[str, list[tuple[str, str | None]]]:
    """The addable components of the committed folder, per kind a list of (name, ID): flows (the name before the ID in
    Workflows/<Name>-<ID>.json, the ID in lower case), variables (the folders under environmentvariabledefinitions/),
    references (connectionreferencelogicalname in Other/Customizations.xml)."""
    flows = sorted((m.group(1), m.group(2).lower()) for p in (folder / "Workflows").glob("*.json")
                   for m in [FLOW_FILE.fullmatch(p.name)] if m)
    variables = sorted((p.name, None) for p in (folder / "environmentvariabledefinitions").iterdir() if p.is_dir()) \
        if (folder / "environmentvariabledefinitions").is_dir() else []
    custom = folder / "Other" / "Customizations.xml"
    references = sorted({(n, None) for n in REFERENCE_NAME.findall(custom.read_bytes().decode("utf-8-sig", "replace"))}) \
        if custom.is_file() else []
    return {"flow": flows, "variable": variables, "reference": references}


def _other_kind(folder: Path, name: str) -> str | None:
    """The kind of a component of the folder that ppp does not add and the name belongs to, in words; None if none."""
    wanted = name.lower()
    canvas = folder / "CanvasApps"
    if canvas.is_dir() and any(p.name.lower().startswith(wanted) and p.name.lower()[len(wanted):][:1] in (".", "_") for p in canvas.iterdir()):
        return "canvas app"
    bots = folder / "botcomponents"
    if bots.is_dir() and any(p.name.lower() == wanted for p in bots.iterdir()):
        return "bot component"
    solution_xml = folder / "Other" / "Solution.xml"
    if solution_xml.is_file():
        text = solution_xml.read_bytes().decode("utf-8-sig", "replace")
        for m in re.finditer(r"<RootComponent\b[^>]*>", text):
            tag = m.group(0)
            kind, schema = re.search(r'\btype="([^"]*)"', tag), re.search(r'\bschemaName="([^"]*)"', tag)
            if kind and schema and schema.group(1).lower() == wanted:
                return OTHER_KINDS.get(kind.group(1), f"component of type {kind.group(1)}")
    return None


def _candidates(items: list[tuple[str, str | None]], part: str) -> str:
    hits = [n for n, _ in items if part.lower() in n.lower()]
    return ", ".join(hits[:SHOWN]) + (", …" if len(hits) > SHOWN else "") if hits else "none"


def _resolve(folder: Path, main: str, name: str, held: dict) -> tuple[str, str, str | None]:
    """(kind, name as the folder spells it, ID or None) of the one component this name is, regardless of case; an
    error that names what is wrong otherwise (ERWEITERUNGEN B.1)."""
    hits = [(kind, n, i) for kind, items in held.items() for n, i in items if n.lower() == name.lower()]
    if len(hits) > 1:
        raise ToolError(f"{name} names {len(hits)} components: " + ", ".join(f"{k} {n}" for k, n, _ in hits) + "; give the full name.")
    if hits:
        return hits[0]
    other = _other_kind(folder, name)
    if other:
        raise ToolError(f"{name} is a {other}; ppp adds flows, environment variables and connection references; other kinds go on a card.")
    raise ToolError(f"No component named {name} in solution/{main}/. Flows: {_candidates(held['flow'], name)}; "
                    f"variables: {_candidates(held['variable'], name)}; references: {_candidates(held['reference'], name)}")


def _used_by(folder: Path, flow: str, held: dict) -> list[tuple[str, str]]:
    """The references and variables a flow uses, each as (kind, name as the main solution spells it): the logical names
    under properties.connectionReferences.*.connection.connectionReferenceLogicalName (as flows.py reads them) and the
    schema names under properties.definition.parameters.*.metadata.schemaName (as setupflow.py reads them). One that
    the main solution does not have is an error; ppp adds nothing then."""
    file = next(p for p in (folder / "Workflows").glob("*.json") if FLOW_FILE.fullmatch(p.name) and FLOW_FILE.fullmatch(p.name).group(1) == flow)
    try:
        data = json.loads(file.read_text(encoding="utf-8-sig"))
        properties = data["properties"]
        wanted = [("reference", str(((r or {}).get("connection") or {}).get("connectionReferenceLogicalName") or ""))
                  for r in (properties.get("connectionReferences") or {}).values()]
        wanted += [("variable", str(((p or {}).get("metadata") or {}).get("schemaName") or ""))
                   for p in ((properties.get("definition") or {}).get("parameters") or {}).values()]
    except (OSError, ValueError, KeyError, AttributeError, TypeError) as ex:
        raise ToolError(f"The flow file {file.name} cannot be read ({ex}): ppp names nothing of what {flow} uses and adds nothing.") from ex
    used = []
    for kind, name in wanted:
        if not name:
            continue
        have = next((n for n, _ in held[kind] if n.lower() == name.lower()), None)
        if have is None:
            raise ToolError(f"The flow {flow} uses the {'connection reference' if kind == 'reference' else 'environment variable'} {name}, "
                            f"which solution/{folder.name}/ does not have: ppp adds nothing.")
        if (kind, have) not in used:
            used.append((kind, have))
    return used


# ------------------------------------------------------------------ checks before any call
def _context(root: Path) -> dict:
    """Environment, main and transfer solution of a project that ppp members works in: connected, role set, mode large,
    a transfer solution other than the main solution, the transfer solution online and not managed (ERWEITERUNGEN B.2)."""
    env = tenant.environment(root)
    connected._need_role(env)
    config = load_config(root)
    main, transfer = solution_with_role(config, "main"), solution_with_role(config, "transfer")
    if config.get("mode") != "large" or not main or not transfer or main.lower() == transfer.lower():
        raise ToolError("ppp members needs mode large and a solution of role transfer in project.json.")
    return {"env": env, "main": main, "transfer": transfer}


def _check_online(env: dict, transfer: str) -> None:
    online = tenant.solutions(env["url"]).get(transfer.lower())
    if not online:
        raise ToolError(f"{transfer} is not in {env['alias']}")
    if online["managed"]:
        raise ToolError(f"{transfer} is managed in {env['alias']}")


def _check_committed(root: Path, folder: Path, main: str) -> None:
    where = gitutil.rel(root, folder) if folder.is_dir() else f"solution/{main}"
    if not folder.is_dir() or not gitutil.is_repo(root) or not gitutil.git(root, "ls-files", "--", where).strip():
        raise ToolError(f"solution/{main}/ is not committed: ppp members takes the names from the committed state; "
                        f"ppp export --solution {main} first.")
    if gitutil.git(root, "status", "--porcelain", "--", where).strip():
        raise ToolError(f"solution/{main}/ has uncommitted changes: ppp members takes the names from the committed state; commit them first.")


# ------------------------------------------------------------------ ppp members
def run(root: Path, names: list[str]) -> int:
    """ppp members [<Name> …] (ERWEITERUNGEN B.1, B.2): without names the line MEMBERS with one line per member; with
    names ADDED, ALREADY and FAILED lines, then the line Next. The checks of B.2 come before any call; the readers are
    tenant.members and tenant.component_ids, the one call that changes the solution is tenant.add_member. Returns the
    exit code: 0 when every named component is a member afterwards, else 1."""
    names = list(dict.fromkeys(n.strip() for n in names if n.strip()))
    context = _context(root)
    env, main, transfer = context["env"], context["main"], context["transfer"]
    if names and env["role"] == "production":
        raise ToolError(f"{env['alias']} has the role production: ppp reads there only.")
    _check_online(env, transfer)
    return _add(root, env, main, transfer, names) if names else _list(root, env, main, transfer)


def _list(root: Path, env: dict, main: str, transfer: str) -> int:
    """The members with the kind and the name the main solution gives them; a member the main solution does not have
    stands as other with its ID. Reading only, so also in an environment of role production, and the folder of the main
    solution need not be committed: it only gives the names."""
    folder = root / "solution" / main
    held = _components(folder) if folder.is_dir() else {"flow": [], "variable": [], "reference": []}
    named: dict[str, tuple[str, str]] = {i: ("flow", n) for n, i in held["flow"]}
    for kind in ("variable", "reference"):
        for name, ids in tenant.component_ids(env["url"], kind, [n for n, _ in held[kind]]).items():
            named.update({i: (kind, name) for i in ids})
    found = tenant.members(env["url"], transfer)
    lines = sorted(f"  {named[i][0]} {named[i][1]}" for i in found if i in named) + sorted(f"  other {i}" for i in found if i not in named)
    print(f"MEMBERS: {transfer} in {env['alias']}: {len(found)}")
    for line in lines:
        print(line)
    print(f"Removing goes on a card (Solutions › {transfer} › Remove from this solution), for members no planned package changes.")
    return 0


def _add(root: Path, env: dict, main: str, transfer: str, names: list[str]) -> int:
    folder = root / "solution" / main
    _check_committed(root, folder, main)
    held = _components(folder)
    # what to add: the named components, each flow with what it uses; a list of [kind, name, with-flow or None]
    plan: list[list] = []

    def want(kind: str, name: str, with_flow: str | None) -> None:
        if not any(p[0] == kind and p[1].lower() == name.lower() for p in plan):
            plan.append([kind, name, with_flow])
    for name in names:
        kind, found, _ = _resolve(folder, main, name, held)
        want(kind, found, None)
    for name in [p[1] for p in plan if p[0] == "flow"]:
        for kind, used in _used_by(folder, name, held):
            want(kind, used, name)
    # the IDs: a flow's in its file name and known to the tenant, a variable and a reference with exactly one row there
    ids: dict[tuple[str, str], str] = {}
    flows = {n.lower(): i for n, i in held["flow"]}
    state = tenant.flows(env["url"], [flows[p[1].lower()] for p in plan if p[0] == "flow"])
    for kind, name, _ in plan:
        if kind == "flow":
            ids[kind, name] = flows[name.lower()]
            if state.get(ids[kind, name]) in (None, "unknown"):
                raise ToolError(f"The flow {name} is not in {env['alias']}: ppp adds nothing; the main solution comes into the environment first.")
    for kind in ("variable", "reference"):
        wanted = [p[1] for p in plan if p[0] == kind]
        for name, found in tenant.component_ids(env["url"], kind, wanted).items():
            if len(found) != 1:
                raise ToolError(f"The {'connection reference' if kind == 'reference' else 'environment variable'} {name} has {len(found)} rows "
                                f"in {env['alias']}: ppp adds only a component with exactly one; nothing is added.")
            ids[kind, name] = found[0]
    label = lambda p: f"{p[0]} {p[1]}" + (f" (with {p[2]})" if p[2] else "")
    present = tenant.members(env["url"], transfer)
    already = [p for p in plan if ids[p[0], p[1]] in present]
    failed: dict[tuple[str, str], str] = {}
    called = [p for p in plan if p not in already]
    for kind, name, _ in called:
        try:
            tenant.add_member(env["url"], transfer, ids[kind, name], kind)
        except TenantError as ex:
            first = str(ex).splitlines()[0]
            failed[kind, name] = first[len("FAILED: "):] if first.startswith("FAILED: ") else first
    after = tenant.members(env["url"], transfer) if called else present
    added = []
    for p in called:
        if (p[0], p[1]) in failed:
            continue
        if ids[p[0], p[1]] in after:
            added.append(p)
        else:
            failed[p[0], p[1]] = "not a member after the call"
    if added:
        print(f"ADDED: {len(added)} new members of {transfer}: " + ", ".join(label(p) for p in added))
    if already:
        print("ALREADY: " + ", ".join(label(p) for p in already) + f" are members of {transfer}.")
    for p in called:
        if (p[0], p[1]) in failed:
            print(f"FAILED: {p[0]} {p[1]}: {failed[p[0], p[1]]}")
    print("Next: ppp export; the transfer solution with its members becomes the base.")
    return 1 if failed else 0
