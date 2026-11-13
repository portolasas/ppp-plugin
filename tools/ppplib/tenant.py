"""The tenant through pac (entwurf/VERBUNDEN.md): one way to call it, with the environment named in every call and a
list of the commands and options ppp uses, and readers for what the tenant holds.

What pac prints is known from the pac test on the company computer (grundlage/werkzeuge/pac-test/TEST_PAC.md, round 1):
- With --json pac prints pure JSON, no line before it: environments, solutions with their version, connections with
  their status.
- pac env fetch prints a table only. Its columns come from the first row: a row that has one value more is shifted
  against the head. So the readers filter on the server, ask for a value that may be empty in a query of its own
  (not-null) and take the values of a row as words; no reader cuts columns by position.
- A choice value stands there as a word of the display language, a time without seconds, a number with a thousands
  separator, an empty result as "No results returned.".
Two calls change more than an import of a package and go only through their own function, which checks them first:
pac solution add-solution-component through add_member (check, guarded), a settings file through start_import, which
hands check the path and SHA-256 of the file it checked (check, settings). Each release opens only its own lock.
A reader that gets a row it cannot read raises SYNTAX; only no row (pac prints "No results returned.") means nothing found.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from xml.sax.saxutils import quoteattr

from . import solution
from .project import ToolError, load_config

GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
KINDS = ("AUTH", "DENIED", "SYNTAX", "TIMEOUT", "BUSY", "FAILED")
# The commands of pac that ppp runs against the tenant, each with the options it may carry, written out and in lower
# case. Anything else is refused: pac reads options without regard to case and takes the last of a repeated one, so a
# list of forbidden options could be written past. Never in this list: delete, publish, --force-overwrite, sign-in,
# admin commands, --publish-changes (it publishes every unpublished change of the whole environment),
# --addrequiredcomponents (it takes components ppp did not name into a solution).
ALLOWED = {
    ("env", "list"): {"--json"},
    ("env", "fetch"): {"--environment", "--xmlfile"},
    ("solution", "list"): {"--environment", "--json"},
    ("solution", "export"): {"--environment", "--name", "--path", "--overwrite", "--async", "--max-async-wait-time"},
    ("solution", "import"): {"--environment", "--path", "--async", "--max-async-wait-time", "--activate-plugins",
                             "--skip-lower-version", "--settings-file"},
    ("connectivity", "list-connections"): {"--environment", "--json"},
    ("solution", "add-solution-component"): {"--environment", "--solutionuniquename", "--component", "--componenttype"},
}
FLAGS = {"--json", "--overwrite", "--async", "--activate-plugins", "--skip-lower-version"}
IMPORT_SWITCHES = ("--async", "--activate-plugins", "--skip-lower-version")  # VERBUNDEN VB-15, decided 2026-11-13
# Two parts of the list go only through the one function that checks them first (ERWEITERUNGEN B.2, C.2), each with a
# release of its own: add_member calls run with guarded=True, which opens add-solution-component and nothing else;
# start_import hands check the settings file it checked (path and SHA-256), and only exactly that file passes. run never
# takes a settings file.
ADD_MEMBER = ("solution", "add-solution-component")     # only through add_member
SETTINGS_FILE = "--settings-file"                       # only through start_import(..., settings=...)
# The kinds of component ppp adds to the transfer solution, in exactly the form pac took them (pac test, T, T4, T6): the
# type code of a connection reference differs per environment (VERBUNDEN VB-13), its name does not.
MEMBER_KINDS = {"flow": "29", "variable": "380", "reference": "connectionreference"}
SOLUTION_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
ALIAS = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")         # the form of structure.slug, the name of environments/<alias>.json
CONNECTOR_ID = "/providers/Microsoft.PowerApps/apis/"
SETTINGS_SECTIONS = {"EnvironmentVariables": ("SchemaName", "Value"), "ConnectionReferences": ("LogicalName", "ConnectionId", "ConnectorId")}


class TenantError(ToolError):
    """A call of pac that did not do what it should. kind: AUTH (no sign-in on this computer), DENIED (no permission),
    SYNTAX (pac knows the command differently, or its output cannot be read), TIMEOUT, BUSY (another import runs),
    FAILED (anything else). After AUTH, DENIED and SYNTAX the step goes to the user on a card."""
    def __init__(self, kind: str, message: str):
        super().__init__(f"{kind}: {message}" + (f"\n{NEXT[kind]}" if kind in NEXT else ""))
        self.kind = kind


NEXT = {    # what the agent does after a failure it cannot repair itself
    "AUTH": "pac is not signed in on this computer. This step goes to the user on a card, as in an offline project; signing in "
            "(pac auth create) is the user's.",
    "DENIED": "The account may not do this in the environment. This step goes to the user on a card.",
    "SYNTAX": "pac takes this call differently than ppp expects. This step goes to the user on a card; write a lesson proposal.",
    "TIMEOUT": "Run the command once more; if it ends the same way, the step goes to the user on a card.",
}


def check(args: list[str], guarded: bool = False, settings: tuple[str, str] | None = None) -> tuple[str, str]:
    """Refuse every call that is not on the list, before pac starts (ERWEITERUNGEN B.2, C.2). No value of an option
    begins with --: pac would read it as the next option. guarded: the release of add_member, for pac solution
    add-solution-component only. settings: the release of start_import, the path and SHA-256 of the settings file it
    checked; --settings-file passes only with exactly that path, and only while the file still has that SHA-256."""
    verb = tuple(args[:2])
    if verb not in ALLOWED:
        raise ToolError(f"pac {' '.join(args[:2])} is not a command ppp runs against the tenant.")
    if verb == ADD_MEMBER and not guarded:
        raise ToolError("pac solution add-solution-component runs only through tenant.add_member.")
    if guarded and verb != ADD_MEMBER:
        raise ToolError(f"pac {' '.join(verb)}: the release of tenant.add_member opens pac solution add-solution-component only.")
    if settings is not None and verb != ("solution", "import"):
        raise ToolError(f"pac {' '.join(verb)}: the release of tenant.start_import opens --settings-file of pac solution import only.")
    seen, values, i = set(), {}, 2
    while i < len(args):
        option = args[i].lower()
        # the environment is ppp's to name: a second one in the call would be read by pac instead of the first
        if not args[i].startswith("--") or option not in ALLOWED[verb] or option in seen or option == "--environment":
            raise ToolError(f"pac {' '.join(verb)}: {args[i]} is not an option ppp uses, or it stands twice.")
        seen.add(option)
        if option not in FLAGS:
            if i + 1 >= len(args):
                raise ToolError(f"pac {' '.join(verb)}: {option} needs a value.")
            if args[i + 1].startswith("--"):
                raise ToolError(f"pac {' '.join(verb)}: the value of {option} is {args[i + 1]}, which pac would read as an option.")
            values[option] = args[i + 1]
        i += 1 if option in FLAGS else 2
    if SETTINGS_FILE in values:
        if settings is None:
            raise ToolError("pac solution import: --settings-file goes only through tenant.start_import, which checks the file first.")
        path, sha = settings
        if values[SETTINGS_FILE] != str(path):
            raise ToolError(f"pac solution import: --settings-file {values[SETTINGS_FILE]} is not the file tenant.start_import checked.")
        if not Path(path).is_file() or solution.sha256(Path(path)).lower() != str(sha).lower():
            raise ToolError(f"pac solution import: the settings file {Path(path).name} changed after tenant.start_import checked it.")
    if verb == ADD_MEMBER:      # the values too: a component at its ID, of one of the three kinds, into a named solution
        if seen != {"--solutionuniquename", "--component", "--componenttype"}:
            raise ToolError("pac solution add-solution-component needs --solutionUniqueName, --component and --componentType.")
        if not SOLUTION_NAME.fullmatch(values["--solutionuniquename"]):
            raise ToolError(f"pac solution add-solution-component: {values['--solutionuniquename']!r} is not the unique name of a solution.")
        if not GUID.fullmatch(values["--component"]):
            raise ToolError(f"pac solution add-solution-component: --component takes the ID of a component, not {values['--component']!r}.")
        if values["--componenttype"] not in MEMBER_KINDS.values():
            raise ToolError(f"pac solution add-solution-component: --componentType {values['--componenttype']} is none of "
                            + ", ".join(MEMBER_KINDS.values()) + ".")
    return verb


def decode(raw: bytes) -> str:
    """pac writes UTF-8 or the console code page, depending on the command."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("oem" if sys.platform == "win32" else "latin-1", "replace")
    return text.replace("\r\n", "\n")


def problem(code: int | None, out: str) -> tuple[str, str] | None:
    """(kind, message) when the call failed, from what pac says itself; the message without the account line. When the
    server rejected an asynchronous operation, pac names its reason in a line of its own before the error line, which
    then only says "The async operation completed with a statuscode of Failed." (pac test 2026-11-12, S7): that reason is
    the message."""
    lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("Connected ")]
    error = next((line for line in lines if line.startswith("Error:")), "")
    reason = next((m.group(1).strip() for m in map(re.compile(r"the reason given was:\s*(.*)", re.I).match, lines) if m), "")
    if code == 0 and not error:
        return None
    text = "\n".join(lines).lower()
    if re.search(r"no profiles were found|pac auth create|aadsts|not authenticated|sign in|login required", text):
        kind = "AUTH"
    elif re.search(r"privilege|permission|access is denied|access denied|not authorized|unauthorized|forbidden|security role", text):
        kind = "DENIED"
    elif re.search(r"^usage: pac |unknown argument|required argument|the value passed to|doesn't support", text, re.M):
        kind = "SYNTAX"
    elif re.search(r"another .{0,40}(import|operation)|import .{0,40}in progress|already running|cannot start .{0,60}while", text):
        kind = "BUSY"
    else:
        kind = "FAILED"
    return kind, (reason or error or (lines[-1] if lines else f"pac ended with exit code {code}"))[:400]


def _command(url: str | None, args: list[str], guarded: bool = False, settings: tuple[str, str] | None = None) -> list[str]:
    verb = check(args, guarded, settings)
    if "--environment" in ALLOWED[verb]:
        if not url:
            raise ToolError(f"pac {' '.join(verb)} needs the address of the environment.")
        args = [*args, "--environment", url]
    return [solution.pac(), *args]


def run(url: str | None, args: list[str], timeout: float = 600, *, guarded: bool = False) -> str:
    """The one way ppp calls pac against the tenant: the environment is named in the call, never taken from pac's profile.
    guarded only from add_member (check); a settings file never goes through run, only through start_import."""
    command = _command(url, args, guarded)
    try:
        proc = subprocess.run(command, capture_output=True, stdin=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise TenantError("TIMEOUT", f"pac {' '.join(args[:2])} did not finish within {int(timeout)} seconds.") from None
    out = decode(proc.stdout) + decode(proc.stderr)
    failed = problem(proc.returncode, out)
    if failed:
        raise TenantError(*failed)
    return out


# ------------------------------------------------------------------ the project's environment
def environment(root: Path, alias: str | None = None) -> dict:
    """The environment a connected project works in: alias, url, role, inUse, confirmImport (VERBUNDEN VB-1, VB-11).
    With alias the environment of environments/<alias>.json instead, a move target say (ERWEITERUNGEN C.2); its
    confirmImport is the project's. own: it is the project's environment."""
    config = load_config(root)
    own = config.get("environment")
    if alias is None:
        alias = own
        if not alias:
            raise ToolError("This project is offline (no environment in project.json): the user exports and imports by hand, "
                            "guided by cards. ppp connect connects it.")
    elif not (isinstance(alias, str) and ALIAS.fullmatch(alias)):
        raise ToolError(f"{alias!r} is not the alias of an environment: the name of a file in environments/ without .json, "
                        "in lower case letters, digits and hyphens.")
    elif not (root / "environments" / f"{alias}.json").is_file():
        raise ToolError(f"environments/{alias}.json does not exist: ppp connect \"<Name>\" --role test --target writes the file of "
                        "a move target.")
    path = root / "environments" / f"{alias}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
    except (OSError, ValueError) as ex:
        raise ToolError(f"environments/{alias}.json cannot be read ({ex}); ppp check names what is wrong.") from ex
    url = str(data.get("environmentUrl") or "").rstrip("/")
    if not url:
        raise ToolError(f"environments/{alias}.json has no environmentUrl yet: run ppp connect.")
    return {"alias": alias, "name": data.get("name") or alias, "url": url, "role": data.get("role"), "inUse": bool(data.get("inUse")),
            "confirmImport": config.get("confirmImport", True), "data": data, "path": path, "own": alias == own}


# ------------------------------------------------------------------ readers: JSON
def _read_json(url: str | None, args: list[str], timeout: float = 600):
    lines = run(url, [*args, "--json"], timeout).splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip().startswith(("[", "{"))), None)
    try:
        if start is None:
            raise ValueError
        return json.loads("\n".join(lines[start:]))
    except ValueError:
        raise TenantError("SYNTAX", f"pac {' '.join(args[:2])} --json printed no JSON; pac may have changed.") from None


def environments() -> list[dict]:
    """Every environment the signed-in user sees: name, url, type."""
    found = []
    for e in _read_json(None, ["env", "list"]):
        if isinstance(e, dict) and e.get("EnvironmentUrl"):
            found.append({"name": str(e.get("FriendlyName") or ""), "url": str(e["EnvironmentUrl"]).rstrip("/"),
                          "type": str((e.get("EnvironmentIdentifier") or {}).get("Type") or "")})
    return found


def find_environment(name: str) -> dict:
    """The environment with exactly this display name, regardless of case and outer blanks; the plugin holds no address,
    the tenant gives it (VERBUNDEN VB-2). A part of a name is never taken: it is named as a suggestion."""
    every = environments()
    wanted = name.strip().lower()
    hits = [e for e in every if e["name"].strip().lower() == wanted]
    if len(hits) == 1:
        return hits[0]
    if hits:
        raise ToolError(f"{len(hits)} environments this sign-in sees are named {name!r}; ppp connects only to a name that is unique.")
    similar = [e["name"] for e in every if wanted and wanted in e["name"].lower()]
    raise ToolError(f"No environment named {name!r} among the {len(every)} this sign-in sees."
                    + (f" Similar names: {', '.join(similar[:6])}; ppp connects only to the full name." if similar else "")
                    + " Give its display name as the Power Platform admin center or make.powerapps.com shows it.")


def solutions(url: str, timeout: float = 600) -> dict[str, dict]:
    """The solutions of the environment by unique name in lower case: name, version, managed, publisher (its unique name,
    pac test round 2, N8)."""
    data = _read_json(url, ["solution", "list"], timeout)
    return {str(s["SolutionUniqueName"]).lower(): {"name": str(s["SolutionUniqueName"]), "version": str(s.get("VersionNumber") or ""),
                                                  "managed": bool(s.get("IsManaged")),
                                                  "publisher": str(s.get("PublisherUniqueName") or "")}
            for s in data if isinstance(s, dict) and s.get("SolutionUniqueName")}


def connections(url: str) -> dict[str, dict]:
    """The connections of the environment by ID: connector and status. Only this list shows a broken connection
    (status Error); pac connection list shows connected ones only."""
    data = _read_json(url, ["connectivity", "list-connections"])
    found = {}
    for c in (data.get("value") if isinstance(data, dict) else data) or []:
        properties = c.get("properties") or {}
        statuses = [str(s.get("status")) for s in properties.get("statuses") or [] if isinstance(s, dict)]
        found[str(c.get("name"))] = {"connector": str(properties.get("apiId") or "").rsplit("/", 1)[-1],
                                     "status": statuses[0] if statuses else ""}
    return found


# ------------------------------------------------------------------ readers: FetchXML
def eq(field: str, value) -> str:
    return f'<condition attribute="{field}" operator="eq" value={quoteattr(str(value))}/>'


def among(field: str, values) -> str:
    return (f'<condition attribute="{field}" operator="in">' + "".join(f"<value>{quoteattr(str(v))[1:-1]}</value>" for v in values)
            + "</condition>")


def empty(field: str) -> str:
    return f'<condition attribute="{field}" operator="null"/>'


def filled(field: str) -> str:
    return f'<condition attribute="{field}" operator="not-null"/>'


def within_hours(field: str, hours: int) -> str:
    return f'<condition attribute="{field}" operator="last-x-hours" value="{hours}"/>'


def query(entity: str, columns: list[str], *conditions: str, more: str = "") -> str:
    """FetchXML without top: pac pages itself, and the server refuses top together with paging."""
    return (f'<fetch><entity name="{entity}">' + "".join(f'<attribute name="{c}"/>' for c in columns)
            + ("<filter>" + "".join(conditions) + "</filter>" if conditions else "") + more + "</entity></fetch>")


def fetch(url: str, xml: str) -> list[str]:
    """The rows of a query, each one line: pac appends the key of the row, so a line with an ID is a row."""
    handle, name = tempfile.mkstemp(prefix="ppp-fetch-", suffix=".xml")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write(xml)
        out = run(url, ["env", "fetch", "--xmlFile", name])
    finally:
        os.unlink(name)
    return [line.rstrip() for line in out.splitlines() if GUID.search(line) and not line.startswith("Connected ")]


def _ids(rows: list[str]) -> set[str]:
    return {g.lower() for row in rows for g in GUID.findall(row)}


def flows(url: str, ids: list[str]) -> dict[str, str]:
    """on, off or unknown per flow ID. The server filters by the number of the state; the table would show a word."""
    if not ids:
        return {}
    wanted = [i.lower() for i in ids]
    state = {n: _ids(fetch(url, query("workflow", ["workflowid"], among("workflowid", wanted), eq("statecode", n)))) for n in (1, 0)}
    return {i: "on" if i in state[1] else "off" if i in state[0] else "unknown" for i in wanted}


def connection_references(url: str, names: list[str]) -> dict[str, dict]:
    """Per logical name: whether the reference exists and the connection it is bound to (None: not bound)."""
    if not names:
        return {}
    base = ("connectionreference", ["connectionreferencelogicalname"])
    present = {row.split()[0].lower() for row in fetch(url, query(*base, among("connectionreferencelogicalname", names)))}
    bound = {row.split()[0].lower(): row.split()[1] for row in fetch(url, query(
        "connectionreference", ["connectionreferencelogicalname", "connectionid"],
        among("connectionreferencelogicalname", names), filled("connectionid"))) if len(row.split()) >= 3}
    return {n: {"exists": n.lower() in present, "connection": bound.get(n.lower())} for n in names}


def variables(url: str, names: list[str]) -> dict[str, dict]:
    """Per schema name: whether the variable exists and its current value (None: none set, the default applies).
    pac appends the key of the row to the asked columns; only that key is taken out of the value, read in the first
    query, where it is the one ID of the row. A value that is an ID itself (of a list, say) stays. Where pac puts the
    column of the linked value, before or after the key, is not shown by the pac test (X9 read the names only): the key
    is taken out wherever it stands, also when it touches the value without a blank."""
    if not names:
        return {}
    keys = {}
    for row in fetch(url, query("environmentvariabledefinition", ["schemaname"], among("schemaname", names))):
        keys[row.split()[0].lower()] = GUID.findall(row)[-1]
    link = ('<link-entity name="environmentvariablevalue" from="environmentvariabledefinitionid" '
            'to="environmentvariabledefinitionid" link-type="inner" alias="v"><attribute name="value"/></link-entity>')
    values = {}
    for row in fetch(url, query("environmentvariabledefinition", ["schemaname"], among("schemaname", names), more=link)):
        name, _, rest = row.strip().partition(" ")
        if name.lower() in keys:
            values[name.lower()] = " ".join(re.sub(re.escape(keys[name.lower()]), " ", rest, count=1, flags=re.I).split())
    return {n: {"exists": n.lower() in keys, "value": values.get(n.lower())} for n in names}


def _unreadable(what: str, row: str) -> TenantError:
    """A row came back that is not in the form the reader knows: an error, never taken for "nothing found". The message
    names its shape, not its values (names and IDs of the tenant stay out of chat)."""
    words, ids = GUID.sub(" ", row).split(), GUID.findall(row)
    return TenantError("SYNTAX", f"pac env fetch returned a row of {what} that ppp cannot read ({len(words)} words, {len(ids)} IDs); "
                                 "pac may have changed.")


def _first_words(rows: list[str], what: str) -> list[str]:
    """The first word of each row, a name before the key of the row; a row that begins with an ID has no name."""
    words = []
    for row in rows:
        if len(row.split()) < 2 or GUID.fullmatch(row.split()[0]):
            raise _unreadable(what, row)
        words.append(row.split()[0])
    return words


def publisher(url: str, unique_name: str, prefix: str, option_prefix: int | str) -> dict:
    """The publisher of this unique name in the environment, and the other publishers that have its prefix or its option
    value prefix (ERWEITERUNGEN A.3). Four queries, none cut by position: the values of a row as words, the display name,
    which has blanks, in a query of its own as the text before the key of the row (the column of the condition may follow
    the key, VERBUNDEN). The option value prefix stands with a thousands separator (pac test round 2, N8: 77,777); its
    digits count. Returns found (uniqueName, displayName, prefix, optionValuePrefix as a number; None: no such publisher,
    only when no row came back), prefix_others and option_others (unique names, sorted, without this publisher). A row
    that came back but is not name, prefix, number and key raises SYNTAX: it is never taken for a missing publisher."""
    columns = ["uniquename", "customizationprefix", "customizationoptionvalueprefix"]
    found = None
    for row in fetch(url, query("publisher", columns, eq("uniquename", unique_name))):
        words = GUID.sub(" ", row).split()
        digits = re.sub(r"\D", "", " ".join(words[2:]))
        if len(words) < 3 or words[0].lower() != unique_name.lower() or not re.fullmatch(r"\d[\d,.  ']*", " ".join(words[2:])):
            raise _unreadable("the publisher", row)
        found = {"uniqueName": words[0], "displayName": "", "prefix": words[1], "optionValuePrefix": int(digits)}
        break
    if found:
        named = fetch(url, query("publisher", ["friendlyname"], eq("uniquename", unique_name)))
        found["displayName"] = GUID.split(named[0], 1)[0].strip() if named else ""
    others = lambda rows: sorted({n for n in _first_words(rows, "a publisher") if n.lower() != unique_name.lower()}, key=str.lower)
    return {"found": found,
            "prefix_others": others(fetch(url, query("publisher", ["uniquename"], eq("customizationprefix", str(prefix).lower())))),
            "option_others": others(fetch(url, query("publisher", ["uniquename"],
                                                     eq("customizationoptionvalueprefix", int(option_prefix)))))}


def members(url: str, solution: str) -> dict[str, str]:
    """The components of a solution (ERWEITERUNGEN B.3): per objectid, in lower case, its kind as the table shows it, a word
    or several of the display language, empty for a connection reference (pac test round 2, T6, W1). The objectid is the
    first ID of the row, the key of the row the last; nothing is filtered by the kind, whose type code for a connection
    reference differs per environment (VERBUNDEN VB-13). A row without the objectid before its key (one ID only, or a
    word before the first ID) raises SYNTAX."""
    link = ('<link-entity name="solution" from="solutionid" to="solutionid" link-type="inner"><filter>'
            + eq("uniquename", solution) + "</filter></link-entity>")
    found = {}
    for row in fetch(url, query("solutioncomponent", ["objectid", "componenttype"], more=link)):
        ids = list(GUID.finditer(row))
        if len(ids) < 2 or row[:ids[0].start()].strip():
            raise _unreadable(f"the members of {solution}", row)
        found[ids[0].group().lower()] = " ".join(row[ids[0].end():ids[-1].start()].split())
    return found


COMPONENT_TABLES = {"reference": ("connectionreference", "connectionreferencelogicalname"),
                    "variable": ("environmentvariabledefinition", "schemaname")}


def component_ids(url: str, kind: str, names: list[str]) -> dict[str, list[str]]:
    """The IDs of connection references (kind reference) or environment variables (kind variable) by their logical or
    schema name (ERWEITERUNGEN B.3): per name as given every ID found, in lower case, the key of the row. One ID per name
    is the only good answer; the caller names any other as an error. A flow's ID is the one in its file name. A row that
    is not one of the names followed by its key raises SYNTAX: the server filters by the names, so it is no empty result."""
    if kind not in COMPONENT_TABLES:
        raise ToolError(f"component_ids reads connection references and environment variables, not {kind!r}.")
    if not names:
        return {}
    entity, column = COMPONENT_TABLES[kind]
    found = {n: [] for n in names}
    for row in fetch(url, query(entity, [column], among(column, names))):
        word = _first_words([row], f"a {column}")[0].lower()
        hits = [n for n in names if n.lower() == word]
        if not hits:
            raise _unreadable(f"a {column}", row)
        for n in hits:
            found[n].append(GUID.findall(row)[-1].lower())
    return found


def running_imports(url: str, name: str, hours: int = 12) -> list[str]:
    """The progress of each import job of the solution that has no end yet."""
    rows = fetch(url, query("importjob", ["solutionname", "progress"], eq("solutionname", name), empty("completedon"),
                            within_hours("createdon", hours)))
    return [row.split()[1] if len(row.split()) >= 3 else "?" for row in rows]


def import_jobs(url: str, name: str, hours: int = 12) -> list[str]:
    """The IDs of every import job of the solution created within the hours, running or ended, in lower case. Read when
    an import starts: its own job is then the one not among them, without a time of the table, whose zone is unknown
    and which has no seconds (VERBUNDEN VB-10)."""
    return sorted(_ids(fetch(url, query("importjob", ["solutionname"], eq("solutionname", name), within_hours("createdon", hours)))))


def import_log(url: str, name: str, hours: int = 12, exclude: list[str] | None = None) -> dict | None:
    """The record of the newest finished import of the solution: results per component and the texts of its errors and
    warnings. With exclude only a job not among these IDs counts (import_jobs before the start: the job of that import).
    None when no such import ended within the hours."""
    order = '<order attribute="createdon" descending="true"/>'
    rows = fetch(url, query("importjob", ["solutionname"], eq("solutionname", name), filled("completedon"),
                            within_hours("createdon", hours), more=order))
    known = {str(j).lower() for j in exclude or ()}
    job = next((g for g in (GUID.findall(row)[-1] for row in rows) if g.lower() not in known), None)
    if job is None:
        return None
    text = "\n".join(fetch(url, query("importjob", ["data"], eq("importjobid", job))))
    count = lambda word: len(re.findall(r"result=(?:\"|&quot;)" + word, text))
    texts = re.findall(r"errortext=(?:\"|&quot;)(.*?)(?:\"|&quot;)", text)
    return {"job": job, "success": count("success"), "warning": count("warning"), "failure": count("failure"),
            "texts": sorted({t.strip()[:300] for t in texts if t.strip()})[:8]}


# ------------------------------------------------------------------ members of a solution
def add_member(url: str, solution: str, component: str, kind: str, timeout: float = 600) -> str:
    """Add one component at its ID to a solution (ERWEITERUNGEN B.2): the one way to pac solution add-solution-component.
    kind is flow, variable or reference, given to pac as 29, 380 and connectionreference; never --AddRequiredComponents,
    never --async. Returns what pac printed; a failed call raises TenantError as run does. Whether the component is a
    member afterwards says members, not the exit code of pac."""
    if kind not in MEMBER_KINDS:
        raise ToolError(f"add_member adds a flow, variable or reference, not {kind!r}.")
    if not (isinstance(component, str) and GUID.fullmatch(component)):
        raise ToolError(f"add_member takes the ID of a component, not {component!r}.")
    if not (isinstance(solution, str) and SOLUTION_NAME.fullmatch(solution)):
        raise ToolError(f"add_member needs the unique name of a solution, not {solution!r}.")
    return run(url, ["solution", "add-solution-component", "--solutionUniqueName", solution, "--component", component,
                     "--componentType", MEMBER_KINDS[kind]], timeout, guarded=True)


# ------------------------------------------------------------------ import
def _settings_refused(settings: Path, why: str) -> ToolError:
    return ToolError(f"The settings file {settings.name} is not imported: {why}. Only ppp import --environment writes it.")


def check_settings(package: Path, settings: Path, settings_sha: str | None) -> None:
    """The checks of a settings file before pac starts (ERWEITERUNGEN C.2): settings_<version of the package>.json in
    exchange/tenant/<target>/<solution of the package>/, beside the package, with the SHA-256 ppp noted when it wrote it;
    a JSON object with the sections EnvironmentVariables (entries SchemaName, Value) and ConnectionReferences (entries
    LogicalName, ConnectionId, ConnectorId) only; every name a component of the package; every connection named, of a
    connector of the Power Platform. A ToolError names the first that fails."""
    info = solution.zip_manifest(package)
    parts = settings.resolve().parts
    if settings.name != f"settings_{info['version']}.json":
        raise _settings_refused(settings, f"its name is not settings_{info['version']}.json, after the version of {package.name}")
    if len(parts) < 5 or parts[-5].lower() != "exchange" or parts[-4].lower() != "tenant" or not ALIAS.fullmatch(parts[-3]) \
            or parts[-2].lower() != info["uniqueName"].lower():
        raise _settings_refused(settings, f"it does not lie in exchange/tenant/<target>/{info['uniqueName']}/")
    if settings.resolve().parent != package.resolve().parent:
        raise _settings_refused(settings, f"it does not lie beside {package.name}")
    if not settings.is_file():
        raise _settings_refused(settings, "it does not exist")
    if not settings_sha or solution.sha256(settings).lower() != str(settings_sha).lower():
        raise _settings_refused(settings, "its SHA-256 is not the one noted when it was written; it changed since")
    try:
        data = json.loads(settings.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as ex:
        raise _settings_refused(settings, f"it is not valid JSON ({ex})") from ex
    if not isinstance(data, dict):
        raise _settings_refused(settings, "it is not a JSON object")
    unknown = sorted(set(data) - set(SETTINGS_SECTIONS))
    if unknown:
        raise _settings_refused(settings, "it has sections other than EnvironmentVariables and ConnectionReferences: " + ", ".join(unknown))
    with zipfile.ZipFile(package) as z:
        names = z.namelist()
        custom = next((z.read(n).decode("utf-8-sig", "replace") for n in names if n.lower() == "customizations.xml"), "")
    have = {"EnvironmentVariables": {n.split("/")[1] for n in names if n.startswith("environmentvariabledefinitions/") and n.count("/") >= 2},
            "ConnectionReferences": set(re.findall(r'connectionreferencelogicalname="([^"]+)"', custom))}
    for section, fields in SETTINGS_SECTIONS.items():
        entries = data.get(section, [])
        if not isinstance(entries, list):
            raise _settings_refused(settings, f"{section} is not a list")
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != set(fields) or not all(isinstance(entry[f], str) for f in fields):
                raise _settings_refused(settings, f"an entry of {section} is not an object with the texts " + ", ".join(fields) + " only")
            name = entry[fields[0]]
            if name not in have[section]:
                raise _settings_refused(settings, f"{section} names {name}, which {package.name} does not have")
            if name in seen:
                raise _settings_refused(settings, f"{section} names {name} twice")
            seen.add(name)
            if section == "ConnectionReferences" and not entry["ConnectionId"].strip():
                raise _settings_refused(settings, f"the ConnectionId of {name} is empty")
            if section == "ConnectionReferences" and not (entry["ConnectorId"].startswith(CONNECTOR_ID)
                                                          and len(entry["ConnectorId"]) > len(CONNECTOR_ID)):
                raise _settings_refused(settings, f"the ConnectorId of {name} does not begin with {CONNECTOR_ID}")


def start_import(url: str, package: Path, wait: float, settings: Path | None = None, settings_sha: str | None = None) -> dict:
    """Hand a package to the server and wait at most `wait` seconds. pac is only the trigger: once it has named the
    asynchronous operation the server holds the import and goes on without pac (pac test round 1, V3), so pac is ended
    after the wait and the state is read from the server (VERBUNDEN VB-10). Returns state: done (pac saw the end),
    running (handed over, pac ended), failed (pac reports an error; kind and message), skipped (pac did not hand the
    package over, the version online is not lower; message). settings: a settings file for a move (ERWEITERUNGEN C.2),
    checked by check_settings against settings_sha before pac starts; the one way to --settings-file."""
    arguments, checked = ["solution", "import", "--path", str(package)], None
    if settings is not None:
        check_settings(Path(package), Path(settings), settings_sha)
        arguments += [SETTINGS_FILE, str(settings)]
        checked = (str(settings), str(settings_sha))
    command = _command(url, [*arguments, *IMPORT_SWITCHES], settings=checked)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    parts: list[bytes] = []
    reader = threading.Thread(target=lambda: parts.extend(iter(proc.stdout.readline, b"")), daemon=True)
    reader.start()
    began = time.monotonic()
    handed_over = lambda: b"asynchronous operation" in b"".join(parts).lower()
    while proc.poll() is None:
        waited = time.monotonic() - began
        if waited > wait and handed_over():
            proc.kill()
            proc.wait(timeout=30)
            return {"state": "running", "seconds": round(waited)}
        if waited > wait + 300:     # the upload itself never came to an end
            proc.kill()
            raise TenantError("TIMEOUT", f"pac did not hand the package to the server within {int(wait + 300)} seconds.")
        time.sleep(0.5)
    reader.join(timeout=10)
    out = decode(b"".join(parts))
    failed = problem(proc.returncode, out)
    if failed:
        return {"state": "failed", "kind": failed[0], "message": failed[1], "seconds": round(time.monotonic() - began)}
    # --skip-lower-version: with a version online that is not lower pac hands nothing over and ends with exit code 0
    # (pac test 2026-11-12, S6)
    skipped = next((line.strip() for line in out.splitlines() if "skipping import" in line.lower()), None)
    if skipped:
        return {"state": "skipped", "message": skipped[:400], "seconds": round(time.monotonic() - began)}
    return {"state": "done", "seconds": round(time.monotonic() - began)}
