"""ppp runs: the runs of the project's flows as the tenant recorded them (entwurf/VERBUNDEN.md VB-21). Reading only,
through tenant.flow_runs, so through pac env fetch on the table flowrun: start, status, and code and error text of a
failed run. The table knows the run, never its actions (pac test round 1, V7; round 3, F2)."""
from __future__ import annotations

import re
from pathlib import Path

from . import tenant
from .project import ToolError, load_config

FLOW_FILE = re.compile(r"(.+)-(" + tenant.GUID.pattern + r")\.json")
SHOWN = 10          # runs listed per flow
ERROR_LENGTH = 600  # characters of an error text


def project_flows(root: Path) -> dict[str, str]:
    """Every flow of the project by its ID in lower case, with the name of its file: the flows of every solution in
    solution/, one that stands in two solutions once."""
    flows: dict[str, str] = {}
    for s in load_config(root).get("solutions") or []:
        folder = root / "solution" / str(s.get("uniqueName")) / "Workflows"
        for p in sorted(folder.glob("*.json")) if folder.is_dir() else []:
            m = FLOW_FILE.fullmatch(p.name)
            if m:
                flows.setdefault(m.group(2).lower(), m.group(1))
    return flows


def run(root: Path, names: list[str], hours: int = 24, failed: bool = False, environment: str | None = None) -> int:
    """ppp runs [<flow> …] [--hours N] [--failed] [--environment <alias>]: per flow a line with the number of runs and
    of failed ones, then its newest runs, a failed one with code and error text. A name is the name of a flow file or a
    part of it, regardless of case. Returns 0 when the table could be read, whatever the runs say."""
    env = tenant.environment(root, environment or None)
    flows = project_flows(root)
    if not flows:
        raise ToolError("No flow in solution/: ppp export brings the flows of the project first.")
    wanted = flows
    if names:
        wanted = {i: n for i, n in flows.items() if any(part.lower() in n.lower() for part in names)}
        missing = [part for part in names if not any(part.lower() in n.lower() for n in flows.values())]
        if missing:
            raise ToolError(f"No flow of the project is named like {', '.join(missing)}. Flows: "
                            + ", ".join(sorted(flows.values(), key=str.lower)) + ".")
    found = tenant.flow_runs(env["url"], list(wanted), hours)
    print(f"Flow runs in {env['alias']}, last {hours} hours; start in UTC, to the minute. A run shows up 3 to 5 minutes "
          "after its start.")
    any_failed = False
    for flow, name in sorted(wanted.items(), key=lambda item: item[1].lower()):
        mine = [r for r in found if r["flow"] == flow]
        bad = [r for r in mine if r["status"] != "Succeeded" or r["error"]]
        any_failed = any_failed or bool(bad)
        if failed and not bad:
            continue
        print(f"  {name}: {len(mine)} runs, {len(bad)} not succeeded" if mine else f"  {name}: no run")
        shown = bad if failed else mine
        for r in shown[:SHOWN]:
            error = ": ".join(t for t in (r["code"], r["error"]) if t)
            print(f"    {r['start']}  {r['status']}" + (f"  {error[:ERROR_LENGTH]}" if error else ""))
        if len(shown) > SHOWN:
            print(f"    … {len(shown) - SHOWN} older")
    if not found:
        print("No run of these flows in the table: none started, or it started less than 5 minutes ago (then the same "
              "command again), or the flow is not in a solution of this environment.")
    elif not any_failed:
        print("Every run ended Succeeded. A wrong result behind it means a Catch handled the failure: the table names no "
              "action. Then the run export answers (tenant-step card: Run history, the run, download, into exchange/).")
    return 0
