"""Reading cloud flow definitions (workflow JSON of a solution export)."""
from __future__ import annotations

import json
import re
from pathlib import Path

LOOPS = ("Foreach", "Until")
CHILD_KEYS = ("actions", "else", "cases", "default")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def definition(flow: dict) -> dict:
    return flow["properties"]["definition"]


def branches(action: dict):
    """(label, actions) for each nested block of an action: Scope/If/Foreach/Until/Switch."""
    if isinstance(action.get("actions"), dict):
        yield "", action["actions"]
    if isinstance((action.get("else") or {}).get("actions"), dict):
        yield "else", action["else"]["actions"]
    for name, case in (action.get("cases") or {}).items():
        if isinstance(case, dict) and isinstance(case.get("actions"), dict):
            yield name, case["actions"]
    if isinstance((action.get("default") or {}).get("actions"), dict):
        yield "default", action["default"]["actions"]


def walk(actions: dict, path: str = "", loops: tuple = (), level: int = 0):
    """Every action as (name, action, path, enclosing loops, nesting level); top level is level 0."""
    for name, action in actions.items():
        yield name, action, path, loops, level
        inner = loops + (name,) if action.get("type") in LOOPS else loops
        for label, sub in branches(action):
            yield from walk(sub, f"{path}/{name}" + (f"/{label}" if label else ""), inner, level + 1)


def own_part(action: dict) -> dict:
    """The action without its nested actions."""
    return {k: v for k, v in action.items() if k not in CHILD_KEYS}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)


def keys(value):
    """Every property name in a nested value."""
    if isinstance(value, list):
        for item in value:
            yield from keys(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from keys(item)


def expressions(s: str) -> tuple[list[str], list[str]]:
    """Expressions in a string: the whole value '@…' or interpolations '@{…}'. Second list: unclosed '@{'."""
    if "@" not in s:
        return [], []
    if s.startswith("@") and not s.startswith("@@") and not s.startswith("@{"):
        return [s[1:]], []
    found, unclosed, k = [], [], 0
    while True:
        k = s.find("@{", k)
        if k < 0:
            break
        if k > 0 and s[k - 1] == "@":
            k += 2
            continue
        depth, quoted, m, end = 0, False, k + 2, -1
        while m < len(s):
            c = s[m]
            if quoted:
                if c == "'":
                    if m + 1 < len(s) and s[m + 1] == "'":
                        m += 2
                        continue
                    quoted = False
            elif c == "'":
                quoted = True
            elif c == "{":
                depth += 1
            elif c == "}":
                if depth == 0:
                    end = m
                    break
                depth -= 1
            m += 1
        if end < 0:
            unclosed.append(s[k:])
            break
        found.append(s[k + 2:end])
        k = end + 1
    return found, unclosed


def literal_property_names(e: str):
    """(function, name) for each setProperty/addProperty in an expression whose name argument is one text literal."""
    for m in re.finditer(r"\b(setProperty|addProperty)\s*\(", e, re.I):
        args, depth, quoted, start, i = [], 0, False, m.end(), m.end()
        while i < len(e) and len(args) < 2:
            c = e[i]
            if quoted:
                if c == "'":
                    if e[i + 1:i + 2] == "'":
                        i += 1
                    else:
                        quoted = False
            elif c == "'":
                quoted = True
            elif c in "([":
                depth += 1
            elif c in ")]" and depth:
                depth -= 1
            elif c in ",)" and depth == 0:
                args.append(e[start:i].strip())
                start = i + 1
                if c == ")":
                    break
            i += 1
        if len(args) == 2 and re.fullmatch(r"'(?:[^']|'')*'", args[1]):
            yield m.group(1), args[1][1:-1].replace("''", "'")


def syntax_problem(e: str) -> str | None:
    """Brackets, strings and empty arguments of one expression."""
    depth, quoted, last, i, n = 0, False, "", 0, len(e)
    while i < n:
        ch = e[i]
        if quoted:
            if ch == "'":
                if i + 1 < n and e[i + 1] == "'":
                    i += 2
                    continue
                quoted = False
                last = "'"
            i += 1
            continue
        if ch == "'":
            quoted = True
            i += 1
            continue
        if ch.isspace():
            i += 1
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            if last == ",":
                return "empty argument before closing bracket"
            depth -= 1
            if depth < 0:
                return "one closing bracket too many"
        elif ch == ",":
            if last in (",", "(", "["):
                return "empty argument"
        last = ch
        i += 1
    if quoted:
        return "string not closed"
    if depth != 0:
        return "brackets not balanced"
    return None


def line_numbers(text: str) -> dict[str, int]:
    """First line of each '"name": {' in the file, for reading only the needed range."""
    found = {}
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r'\s*"((?:[^"\\]|\\.)*)":\s*\{', line)
        if m and m.group(1) not in found:
            found[m.group(1)] = i
    return found


def inventory(path: Path) -> list[str]:
    """Trigger, connection references and the action tree with type, line and runAfter."""
    text = path.read_text(encoding="utf-8-sig")
    flow = json.loads(text)
    lines = line_numbers(text)
    d = definition(flow)
    out = [f"=== {path.name}  (lines: {len(text.splitlines())})"]
    for name, ref in (flow["properties"].get("connectionReferences") or {}).items():
        logical = (ref.get("connection") or {}).get("connectionReferenceLogicalName", "")
        out.append(f"  ConnRef {name} -> {logical}")
    for name, trig in (d.get("triggers") or {}).items():
        op = ((trig.get("inputs") or {}).get("host") or {}).get("operationId", "") if isinstance(trig.get("inputs"), dict) else ""
        kind = f"/{trig['kind']}" if trig.get("kind") else ""
        out.append(f"  TRIGGER {name} [{trig.get('type')}{kind}{' ' + op if op else ''}]")

    def tree(actions: dict, depth: int):
        for name, a in actions.items():
            ra = a.get("runAfter") or {}
            after = " <- " + ", ".join(f"{k}:{'/'.join(v)}" for k, v in ra.items()) if ra else ""
            inputs = a.get("inputs") if isinstance(a.get("inputs"), dict) else {}
            op = (inputs.get("host") or {}).get("operationId", "")
            out.append("  " * (depth + 1) + f"- {name} [{a.get('type')}{' ' + op if op else ''}] L{lines.get(name, 0)}{after}")
            for label, sub in branches(a):
                if label:
                    out.append("  " * (depth + 2) + ("ELSE:" if label == "else" else "DEFAULT:" if label == "default" else f"CASE {label}:"))
                    tree(sub, depth + 2)
                else:
                    tree(sub, depth + 1)

    tree(d.get("actions") or {}, 0)
    all_actions = list(walk(d.get("actions") or {}))
    depth = max((lvl for *_, lvl in all_actions), default=0)
    out.append(f"  ({len(all_actions)} actions, nesting depth {depth})")
    return out
