"""Checks of a solution folder before packing (successor of PPP-CHECK C1–C11, plus C12–C14).

The base is a git commit (default: the commit that brought the current solution version, see gitutil.base_commit).
Flow checks C7–C13 run on changed flows; with check_all on every flow.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.dom.minidom
from pathlib import Path

from . import flows, refpaths
from .gitutil import read_blobs, rel, tracked_files, version_of
from .report import Report

FORBIDDEN = ("createObject", "padLeft")
MAX_DEPTH = 8  # Power Automate rejects actions nested deeper than level 8, top level = 0 (PA-20261008-MAC-01)
BOOL_RX = re.compile(r"string\(\s*(or|and|not|equals|greater|greaterOrEquals|less|lessOrEquals|empty|contains|startsWith|endsWith|bool)\(")
REF_RX = re.compile(r"\b(outputs|body|actions|result|items|variables)\(\s*'([^']+)'\s*\)")
SET_VARIABLE = ("SetVariable", "AppendToArrayVariable", "AppendToStringVariable")
CHANGE_VARIABLE = SET_VARIABLE + ("IncrementVariable", "DecrementVariable")
SOLUTION_XML = "Other/Solution.xml"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _bom(b: bytes) -> bool:
    return b[:3] == b"\xef\xbb\xbf"


def _short(text: str, n: int = 90) -> str:
    return text if len(text) <= n else text[:n] + "…"


def files_of(folder: Path) -> list[str]:
    """Files of a solution folder; hidden files such as .DS_Store are no part of the solution."""
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*")
                  if p.is_file() and not any(part.startswith(".") for part in p.relative_to(folder).parts))


def canvas_apps(folder: Path) -> list[str]:
    return sorted(p.name[:-len(".meta.xml")] for p in (folder / "CanvasApps").glob("*.meta.xml"))


def _parse(name: str, data: bytes) -> str | None:
    try:
        if name.endswith(".json"):
            json.loads(data.decode("utf-8-sig"))
        elif name.endswith(".xml"):
            xml.dom.minidom.parseString(data)
    except Exception as ex:  # noqa: BLE001 – any parse error is a finding
        return str(ex)
    return None


def _conditions(actions: dict) -> dict[str, str]:
    """Conditions (If) with their expression string; structured ones as '<structured>'."""
    found = {}
    for name, a, *_ in flows.walk(actions):
        if a.get("type") == "If":
            found[name] = a["expression"] if isinstance(a.get("expression"), str) else "<structured>"
    return found


def check_flow(rep: Report, short: str, text: str, base_text: str | None, retry_none: list[str], retry_seen: set) -> None:
    flow = json.loads(text)
    actions = flows.definition(flow).get("actions") or {}
    every = list(flows.walk(actions))

    # C7 runAfter only on siblings, unique names
    def siblings(acts: dict, path: str):
        for name, a in acts.items():
            for dep in a.get("runAfter") or {}:
                if dep not in acts:
                    rep.error(f"C7 {short} :: {name} runAfter '{dep}' is not on the same level ({path})")
            for label, sub in flows.branches(a):
                siblings(sub, f"{path}/{name}" + (f"/{label}" if label else ""))

    siblings(actions, "")
    names = [n for n, *_ in every]
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        rep.error(f"C7 {short} :: duplicate action names: {', '.join(dups)}")

    variables = set()
    for _, a, *_ in every:
        if a.get("type") == "InitializeVariable":
            for v in (a.get("inputs") or {}).get("variables") or []:
                variables.add(v.get("name"))
    by_name = {n: (a, loops) for n, a, _, loops, _ in every}

    for name, a, _, loops, _ in every:
        t = a.get("type")
        inputs = a.get("inputs")
        # C10 Terminate in loops, URI and filter fields made of one expression
        if t == "Terminate" and loops:
            rep.error(f"C10 {short} :: {name} (Terminate) is inside a loop (Foreach/Until); saving fails "
                      "(InvalidWorkflowRunAction). Collect errors, terminate after the loop.")
        if isinstance(inputs, dict):
            fields = [("uri", inputs["uri"])] if "uri" in inputs else []
            fields += [(k, v) for k, v in (inputs.get("parameters") or {}).items() if re.search(r"(^|/)(uri|\$filter|\$orderby)$", k)]
            for field, value in fields:
                if isinstance(value, str) and value.startswith("@") and not value.startswith("@{"):
                    msg = (f"C10 {short} :: {name} field '{field}' consists of one expression ({value[:50]}...). "
                           "Fixed text first, dynamic parts as @{...}.")
                    rep.error(msg) if field.endswith("uri") else rep.warn(msg)
        # C7 SetVariable/Append… with value, without reading itself
        if t in SET_VARIABLE:
            inputs = inputs if isinstance(inputs, dict) else {}
            vn = inputs.get("name")
            if "value" not in inputs or inputs.get("value") == "":
                rep.error(f"C7 {short} :: {name} ({t}) has an empty or missing value. The designer requires a value; "
                          "use a sentinel literal, for example.")
            else:
                value = inputs["value"] if isinstance(inputs["value"], str) else json.dumps(inputs["value"])
                if re.search(r"variables\((\\u0027|')" + re.escape(str(vn)) + r"(\\u0027|')\)", value):
                    rep.error(f"C7 {short} :: {name} ({t}) reads its own variable '{vn}' (self reference)")
        # C7 request bodies
        body = None
        if isinstance(inputs, dict):
            if "body" in inputs:
                body = inputs["body"]
            elif "parameters/body" in (inputs.get("parameters") or {}):
                body = inputs["parameters"]["parameters/body"]
        if body is not None and t != "ParseJson":
            text_body = body if isinstance(body, str) else json.dumps(body)
            if "json(" in text_body:
                rep.warn(f"C7 {short} :: {name} body contains json(...). json() is no serializer; JSON-escape text values.")
            if BOOL_RX.search(text_body):
                rep.warn(f"C7 {short} :: {name} body serializes a Boolean with string(...). True/False is no JSON; "
                         "use if(<bool>,'true','false').")

    # C8 conditions in structured form
    current_if = _conditions(actions)
    base_if = {}
    if base_text:
        try:
            base_if = _conditions(flows.definition(json.loads(base_text)).get("actions") or {})
        except (ValueError, KeyError):
            pass
    legacy = []
    for k, v in current_if.items():
        if v == "<structured>":
            continue
        if base_if.get(k) != v:
            rep.error(f"C8 {short} :: condition {k} as an expression string (cannot be shown in the designer and is lost "
                      "on editing). Use the structured form and/or/not + equals ...")
        else:
            legacy.append(k)
    if legacy:
        rep.warn(f"C8 {short} :: {len(legacy)} existing conditions as expression strings (do not edit in the designer): "
                 + ", ".join(sorted(legacy)))

    # C9 expression syntax
    n_expr, bad9 = 0, 0
    for s in flows.strings(flows.definition(flow)):
        found, unclosed = flows.expressions(s)
        for u in unclosed:
            bad9 += 1
            rep.error(f"C9 {short} :: interpolation @{{ … }} not closed :: {_short(u)}")
        for e in found:
            n_expr += 1
            problem = flows.syntax_problem(e)
            if problem:
                bad9 += 1
                if bad9 <= 10:
                    rep.error(f"C9 {short} :: expression: {problem} :: {_short(e)}")
    for key in flows.keys(flows.definition(flow)):
        # a key is read as an expression too: '@odata.nextLink' in a schema failed the import (PA-20261024-WIN-01)
        if key.startswith("@") and not key.startswith(("@@", "@{")):
            bad9 += 1
            if bad9 <= 10:
                rep.error(f"C9 {short} :: property name {key} is read as an expression; write @{key} for a literal @")
    if bad9 > 10:
        rep.error(f"C9 {short} :: {bad9 - 10} more faulty expressions")
    rep.info(f"C9 {short} :: {n_expr} expressions checked for syntax")

    # C11 references to actions, variables and loops
    bad11 = 0
    for name, a, _, loops, _ in every:
        if a.get("type") in CHANGE_VARIABLE and (a.get("inputs") or {}).get("name") not in variables:
            bad11 += 1
            rep.error(f"C11 {short} :: {name} sets unknown variable '{(a.get('inputs') or {}).get('name')}'")
        for s in flows.strings(flows.own_part(a)):
            if "@" not in s:
                continue
            for fn, arg in REF_RX.findall(s):
                if fn == "variables":
                    if arg not in variables:
                        bad11 += 1
                        rep.error(f"C11 {short} :: {name} reads unknown variable '{arg}'")
                elif fn == "items":
                    if arg not in loops:
                        bad11 += 1
                        rep.error(f"C11 {short} :: {name} uses items('{arg}') outside that loop")
                elif arg not in by_name:
                    bad11 += 1
                    rep.error(f"C11 {short} :: {name} refers to unknown action '{arg}'")
                else:
                    foreign = [lp for lp in by_name[arg][1] if lp not in loops]
                    if foreign:
                        rep.warn(f"C11 {short} :: {name} reads '{arg}' from a foreign loop ({foreign[0]})")
    if not bad11:
        rep.ok(f"C11 {short} :: references to actions, variables and loops resolved")

    # C7 functions missing in Power Automate, retry policies
    for fn in FORBIDDEN:
        n = len(re.findall(r"\b" + re.escape(fn) + r"\s*\(", text))
        if n:
            rep.error(f"C7 {short} :: function {fn}() occurs {n} times (not available)")
    n = len(re.findall(r"\bcreateArray\(\s*\)", text))
    if n:  # imports, then fails at run time (PA-20261024-WIN-02)
        rep.error(f"C7 {short} :: createArray() without arguments occurs {n} times; it fails at run time, use json('[]')")
    for rn in retry_none:
        if rn not in by_name:
            continue
        retry_seen.add(rn)
        policy = ((by_name[rn][0].get("inputs") or {}).get("retryPolicy") or {}) if isinstance(by_name[rn][0].get("inputs"), dict) else {}
        if policy.get("type") == "none":
            rep.ok(f"C7 {short} :: {rn} retryPolicy = none")
        else:
            rep.error(f"C7 {short} :: {rn} without retryPolicy none")
    rep.info(f"C7 {short} :: {len(every)} actions checked")

    # C12 nesting depth
    too_deep = [n for n, *_, lvl in every if lvl > MAX_DEPTH]
    depth = max((lvl for *_, lvl in every), default=0)
    if too_deep:
        rep.error(f"C12 {short} :: nesting deeper than level {MAX_DEPTH} (Power Automate rejects it): "
                  + ", ".join(too_deep[:8]) + (f" and {len(too_deep) - 8} more" if len(too_deep) > 8 else ""))
    else:
        rep.ok(f"C12 {short} :: nesting depth {depth}/{MAX_DEPTH}")

    # C13 reference paths
    findings, _, root_note = refpaths.check(flow)
    for f in findings[:10]:
        rep.error(f"C13 {short} :: {f}")
    if len(findings) > 10:
        rep.error(f"C13 {short} :: {len(findings) - 10} more reference path findings")
    if not findings:
        rep.ok(f"C13 {short} :: every referenced action lies on a runAfter or scope path")
    if root_note:
        rep.warn(f"C13 {short} :: {root_note}")


def verify(root: Path, folder: Path, base: str, *, allowed: list[str] | None = None, retry_none: list[str] | None = None,
           check_all: bool = False, with_apps: bool = False, version_required: bool = True) -> Report:
    """version_required: False for ppp verify during the build; there ppp pack has not raised the version yet."""
    allowed = allowed or []
    retry_none = retry_none or []
    rep = Report(f"ppp verify | {rel(root, folder)} | base {base[:10]}")
    prefix = rel(root, folder) + "/"
    base_files = tracked_files(root, base, folder)
    base_data = read_blobs(root, base, [prefix + f for f in base_files])
    base_data = {k[len(prefix):]: v for k, v in base_data.items()}
    current = files_of(folder)
    data = {f: (folder / f).read_bytes() for f in current}

    # C1 file set
    missing = [f for f in base_files if f not in data]
    extra = [f for f in current if f not in base_data]
    if not missing and not extra:
        rep.ok(f"C1 files: {len(current)} as in the base")
    else:
        rep.error("C1 files differ from the base. Missing: " + (", ".join(missing) or "-") + " | Added: "
                  + (", ".join(extra) or "-") + ". New components come from the tenant via export.")

    # C2/C3 parse
    bad = 0
    for f in current:
        problem = _parse(f, data[f])
        if problem:
            bad += 1
            rep.error(f"{'C2 JSON' if f.endswith('.json') else 'C3 XML'} not parsable: {f} :: {problem}")
    if not bad:
        rep.ok("C2/C3 all JSON and XML files parsable")

    # C4 changed files
    changed = [f for f in current if f in base_data and _sha(data[f]) != _sha(base_data[f])]
    rep.info(f"C4 changed files ({len(changed)}): " + (", ".join(changed) or "-"))
    if allowed:
        not_allowed = [f for f in changed if f != SOLUTION_XML and f not in allowed]
        if not_allowed:
            rep.error("C4 changes not released: " + ", ".join(not_allowed))
        else:
            rep.ok("C4 only released files changed, the rest is byte-identical")

    # C5 version
    vb, vc = version_of(base_data.get(SOLUTION_XML, b"")), version_of(data.get(SOLUTION_XML, b""))
    try:
        if tuple(map(int, vc.split("."))) > tuple(map(int, vb.split("."))):
            rep.ok(f"C5 version {vb} -> {vc}")
        elif version_required:
            rep.error(f"C5 version not increased ({vb} -> {vc})")
        else:
            rep.info(f"C5 version not increased yet ({vb} -> {vc}); ppp pack --version <next> sets it")
    except (AttributeError, ValueError):
        rep.error(f"C5 version not readable (base {vb}, current {vc})")

    # C6 BOM and line endings of changed files
    for f in changed:
        bc, br = data[f], base_data[f]
        if f.startswith("Workflows/") and f.endswith(".json") and _bom(bc):
            rep.error(f"C6 BOM in workflow JSON: {f}")
        elif _bom(bc) != _bom(br):
            rep.warn(f"C6 BOM state changed ({_bom(br)} -> {_bom(bc)}): {f}")
        crc, lfc = bc.count(b"\r\n"), len(re.findall(rb"(?<!\r)\n", bc))
        crr, lfr = br.count(b"\r\n"), len(re.findall(rb"(?<!\r)\n", br))
        if crc and lfc:
            rep.warn(f"C6 mixed line endings (CRLF {crc} / LF {lfc}): {f}")
        elif (crr and not crc and lfc) or (lfr and not crr and crc):
            rep.warn(f"C6 line ending style changed: {f}")

    # C7–C13 flows
    flow_files = [f for f in current if f.startswith("Workflows/") and f.endswith(".json")]
    targets = flow_files if check_all else [f for f in flow_files if f in changed or f in extra]
    retry_seen: set = set()
    for f in targets:
        short = f.split("/")[-1]
        try:
            text = data[f].decode("utf-8-sig")
            json.loads(text)
        except ValueError:
            continue  # reported by C2
        base_text = base_data[f].decode("utf-8-sig") if f in base_data else None
        check_flow(rep, short, text, base_text, retry_none, retry_seen)
    for rn in retry_none:
        if rn not in retry_seen:
            rep.warn(f"C7 RetryNone action not found in the checked flows: {rn}")

    # C14 apps stay outside the package (A-7, Ü-10)
    apps = canvas_apps(folder)
    if apps and not with_apps:
        rep.error("C14 the solution contains apps: " + ", ".join(apps) + ". A package excludes apps (A-7): remove them "
                  "from the solution in the tenant, export again, then pack. Only a move to test or production packs apps (--with-apps).")
    elif apps:
        rep.info("C14 apps packed on purpose: " + ", ".join(apps))
    else:
        rep.ok("C14 no apps in the solution")
    return rep
