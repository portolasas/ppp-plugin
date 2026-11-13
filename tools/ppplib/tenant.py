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
from pathlib import Path
from xml.sax.saxutils import quoteattr

from . import solution
from .project import ToolError, load_config

GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
KINDS = ("AUTH", "DENIED", "SYNTAX", "TIMEOUT", "BUSY", "FAILED")
# The commands of pac that ppp runs against the tenant, each with the options it may carry, written out and in lower
# case. Anything else is refused: pac reads options without regard to case and takes the last of a repeated one, so a
# list of forbidden options could be written past. Never in this list: delete, publish, --force-overwrite, sign-in,
# admin commands, --publish-changes (it publishes every unpublished change of the whole environment).
ALLOWED = {
    ("env", "list"): {"--json"},
    ("env", "fetch"): {"--environment", "--xmlfile"},
    ("solution", "list"): {"--environment", "--json"},
    ("solution", "export"): {"--environment", "--name", "--path", "--overwrite", "--async", "--max-async-wait-time"},
    ("solution", "import"): {"--environment", "--path", "--async", "--max-async-wait-time", "--activate-plugins",
                             "--skip-lower-version"},
    ("connectivity", "list-connections"): {"--environment", "--json"},
}
FLAGS = {"--json", "--overwrite", "--async", "--activate-plugins", "--skip-lower-version"}
IMPORT_SWITCHES = ("--async", "--activate-plugins", "--skip-lower-version")  # VERBUNDEN VB-15, decided 2026-11-13


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


def check(args: list[str]) -> tuple[str, str]:
    """Refuse every call that is not on the list, before pac starts."""
    verb = tuple(args[:2])
    if verb not in ALLOWED:
        raise ToolError(f"pac {' '.join(args[:2])} is not a command ppp runs against the tenant.")
    seen, i = set(), 2
    while i < len(args):
        option = args[i].lower()
        # the environment is ppp's to name: a second one in the call would be read by pac instead of the first
        if not args[i].startswith("--") or option not in ALLOWED[verb] or option in seen or option == "--environment":
            raise ToolError(f"pac {' '.join(verb)}: {args[i]} is not an option ppp uses, or it stands twice.")
        seen.add(option)
        i += 1 if option in FLAGS else 2
        if i > len(args):
            raise ToolError(f"pac {' '.join(verb)}: {option} needs a value.")
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


def _command(url: str | None, args: list[str]) -> list[str]:
    verb = check(args)
    if "--environment" in ALLOWED[verb]:
        if not url:
            raise ToolError(f"pac {' '.join(verb)} needs the address of the environment.")
        args = [*args, "--environment", url]
    return [solution.pac(), *args]


def run(url: str | None, args: list[str], timeout: float = 600) -> str:
    """The one way ppp calls pac against the tenant: the environment is named in the call, never taken from pac's profile."""
    command = _command(url, args)
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
def environment(root: Path) -> dict:
    """The environment a connected project works in: alias, url, role, inUse, confirmImport (VERBUNDEN VB-1, VB-11)."""
    config = load_config(root)
    alias = config.get("environment")
    if not alias:
        raise ToolError("This project is offline (no environment in project.json): the user exports and imports by hand, "
                        "guided by cards. ppp connect connects it.")
    path = root / "environments" / f"{alias}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as ex:
        raise ToolError(f"environments/{alias}.json cannot be read ({ex}); ppp check names what is wrong.") from ex
    url = str(data.get("environmentUrl") or "").rstrip("/")
    if not url:
        raise ToolError(f"environments/{alias}.json has no environmentUrl yet: run ppp connect.")
    return {"alias": alias, "name": data.get("name") or alias, "url": url, "role": data.get("role"), "inUse": bool(data.get("inUse")),
            "confirmImport": config.get("confirmImport", True), "data": data, "path": path}


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
    """The solutions of the environment by unique name in lower case: name, version, managed."""
    data = _read_json(url, ["solution", "list"], timeout)
    return {str(s["SolutionUniqueName"]).lower(): {"name": str(s["SolutionUniqueName"]), "version": str(s.get("VersionNumber") or ""),
                                                  "managed": bool(s.get("IsManaged"))}
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


# ------------------------------------------------------------------ import
def start_import(url: str, package: Path, wait: float) -> dict:
    """Hand a package to the server and wait at most `wait` seconds. pac is only the trigger: once it has named the
    asynchronous operation the server holds the import and goes on without pac (pac test round 1, V3), so pac is ended
    after the wait and the state is read from the server (VERBUNDEN VB-10). Returns state: done (pac saw the end),
    running (handed over, pac ended), failed (pac reports an error; kind and message), skipped (pac did not hand the
    package over, the version online is not lower; message)."""
    command = _command(url, ["solution", "import", "--path", str(package), *IMPORT_SWITCHES])
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
