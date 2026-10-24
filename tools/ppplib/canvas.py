"""Check screen YAML for "paste code" and convert App.Formulas from en-US to de-DE (successor of PPP-CANVAS).

Lessons: PAPPS-20260930-MAC-01…06, PAPPS-20261006-MAC-01, PAPPS-20261007-MAC-01/02, PAPPS-20261024-WIN-01. Matching is case-insensitive
where PPP-CANVAS used PowerShell's -match, -like and -eq.
"""
from __future__ import annotations

import re
from pathlib import Path

from .report import Report

OPEN, CLOSE = "([{", ")]}"


def brackets(f: str) -> str | None:
    """Brackets, strings and 'identifiers' balanced; // comments skipped."""
    stack, i, n = [], 0, len(f)
    while i < n:
        c = f[i]
        if c == '"':
            j = i + 1
            while j < n:
                if f[j] == '"':
                    if j + 1 < n and f[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            if j >= n:
                return "string not closed"
            i = j + 1
            continue
        if c == "'":
            j = f.find("'", i + 1)
            if j < 0:
                return "identifier not closed"
            i = j + 1
            continue
        if c == "/" and i + 1 < n and f[i + 1] == "/":
            j = f.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in OPEN:
            stack.append(c)
        elif c in CLOSE:
            if not stack or stack.pop() != OPEN[CLOSE.index(c)]:
                return f"bracket {c} at position {i} does not match"
        i += 1
    return "open brackets: " + "".join(reversed(stack)) if stack else None


def to_de(src: str) -> str:
    """en-US to de-DE outside strings, 'identifiers' and // comments (same rule as blocks/pfx.py)."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == '"':
            j = i + 1
            while j < n:
                if src[j] == '"':
                    if j + 1 < n and src[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            e = min(j, n - 1)
            out.append(src[i:e + 1])
            i = e + 1
        elif c == "'":
            j = src.find("'", i + 1)
            j = n - 1 if j < 0 else j
            out.append(src[i:j + 1])
            i = j + 1
        elif c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(src[i:j])
            i = j
        elif c == ";":
            out.append(";;")
            i += 1
        elif c == ",":
            out.append(";")
            i += 1
        elif c == "." and 0 < i < n - 1 and src[i - 1].isdigit() and src[i + 1].isdigit():
            out.append(",")
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _call(s: str, opening: int) -> str:
    """Text of a call from its opening bracket (strings already blanked)."""
    depth = 0
    for q in range(opening, len(s)):
        ch = s[q]
        if ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth -= 1
            if depth == 0:
                return s[opening + 1:q]
    return s[opening + 1:]


def _args(inner: str) -> list[str]:
    parts, depth, start = [], 0, 0
    for q, ch in enumerate(inner):
        if ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(inner[start:q])
            start = q + 1
    parts.append(inner[start:])
    return parts


def sources_regex(sources: str) -> re.Pattern | None:
    names = [s for s in re.split(r"[,;\s]+", sources or "") if s]
    if not names:
        return None
    alt = "|".join(re.escape(s).replace(r"\*", "[A-Za-z0-9_]*") for s in names)
    return re.compile(r"^\s*'?(" + alt + r")'?\s*$", re.I)


def allowed_versions(text: str) -> set[str]:
    return {m.group(1).lower() for m in re.finditer(r"([A-Za-z][A-Za-z/]*@\d+(\.\d+)*)", text)}


def parse_yaml(lines: list[str]):
    """Controls (name, indent, type, properties) and properties (control, key, value) of a screen file."""
    controls, props = [], []
    current, prop_indent, i = None, -1, 0
    while i < len(lines):
        z = lines[i]
        indent = len(z) - len(z.lstrip(" "))
        t = z.strip()
        m = re.match(r"^- ([A-Za-z0-9_]+):$", t, re.I)
        if m:
            current = {"name": m.group(1), "indent": indent, "type": "", "props": {}}
            controls.append(current)
            prop_indent, i = -1, i + 1
            continue
        m = re.match(r"^([A-Za-z0-9_]+):$", t, re.I)
        if m and indent <= 2:
            current = {"name": m.group(1), "indent": indent, "type": "Screen", "props": {}}
            controls.append(current)
            prop_indent, i = -1, i + 1
            continue
        m = re.match(r"^Control:\s*(\S+)$", t, re.I)
        if m and current:
            current["type"] = m.group(1)
            i += 1
            continue
        if t.lower() == "properties:":
            prop_indent, i = indent + 2, i + 1
            continue
        if t.lower() == "children:":
            prop_indent, i = -1, i + 1
            continue
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", t)
        if prop_indent >= 0 and indent == prop_indent and m:
            key, value = m.group(1), m.group(2)
            if value.startswith("|"):
                buf, i = [], i + 1
                while i < len(lines):
                    w = lines[i]
                    if w.strip() and len(w) - len(w.lstrip(" ")) <= prop_indent:
                        break
                    buf.append(w.strip())
                    i += 1
                value = "\n".join(buf).strip()
            else:
                i += 1
            if current:
                current["props"][key] = value
            props.append((current["name"] if current else "?", key, value))
            continue
        i += 1
    return controls, props


def check(files: list[Path], versions: set[str] | None, sources: re.Pattern | None, rep: Report) -> tuple[int, int]:
    """Findings into the report; returns (controls, formulas)."""
    n_ctl = n_fx = 0
    filters = matched = 0
    for path in files:
        short = path.name
        controls, props = parse_yaml(path.read_bytes().decode("utf-8-sig").splitlines())
        for ctl, key, value in props:
            n_fx += 1
            where = f"{short} :: {ctl}.{key}"
            if not value.startswith("="):
                rep.error(f"{where} :: value does not start with '='")
                continue
            f = value[1:]
            problem = brackets(f)
            if problem:
                rep.error(f"{where} :: {problem}")
            plain = re.sub(r'"([^"]|"")*"', '""', f)
            if ";;" in plain:
                rep.error(f"{where} :: ';;' in YAML; YAML is always en-US (comma format)")
            if key.lower() == "layoutmode":
                rep.error(f"{where} :: LayoutMode in YAML (auto layout only through Variant)")
            if re.search(r'Coalesce\([^()"]*,\s*""\)\s*=\s*""', f, re.I):
                rep.error(f'{where} :: Coalesce(x, "") = "": check with IsBlank(x) (PAPPS-20260930-MAC-02)')
            for m in re.finditer(r"\bIfError\(", plain):
                args = _args(_call(plain, m.end() - 1))
                if len(args) >= 2 and re.search(r"\.Run\(", args[0], re.I) and args[-1].strip().lower() == "blank()":
                    rep.warn(f"{where} :: IfError(<… .Run( …>, Blank()) swallows the cause; show FirstError.Message")
                    break
            if sources:
                for m in re.finditer(r"\bFilter\(", plain):
                    inner = _call(plain, m.end() - 1)
                    args = _args(inner)
                    filters += 1
                    if not sources.search(args[0]):
                        continue
                    matched += 1
                    if re.search(r"IsBlank\([^()]*\)\s*\|\|", inner, re.I):
                        rep.warn(f"{where} :: Filter({args[0].strip()}, … IsBlank(x) || …) breaks delegation (PAPPS-20261006-MAC-01)")
                        break
                    if re.search(r"\.Value\s*<>", inner, re.I):
                        rep.warn(f"{where} :: Filter({args[0].strip()}, … .Value <> …) breaks delegation on a choice column; "
                                 "join = with || over the allowed values (PAPPS-20261024-WIN-01)")
                        break
                run = plain.find(".Run(")
                if run >= 0 and not re.search(r"Refresh\(", plain, re.I):
                    for m in re.finditer(r"\bClearCollect\(", plain):
                        if m.start() < run:
                            continue
                        args = _args(_call(plain, m.end() - 1))
                        if len(args) >= 2 and sources.search(args[1]):
                            rep.warn(f"{where} :: ClearCollect(…, {args[1].strip()}) after .Run( without Refresh( (PAPPS-20260930-MAC-03)")
                            break
        for c, x in enumerate(controls):
            if x["type"] in ("Screen", ""):
                continue
            n_ctl += 1
            if versions is not None and x["type"].lower() not in versions:
                rep.error(f"{short} :: {x['name']} :: {x['type']} not in the version table (probe)")
            props_lower = {k.lower(): v for k, v in x["props"].items()}
            if x["type"].lower().startswith("groupcontainer@"):
                if "radiustopleft" not in props_lower or "borderthickness" not in props_lower:
                    rep.warn(f"{short} :: {x['name']} :: container without Radius/BorderThickness; Studio sets rounding "
                             "and border (PAPPS-20260930-MAC-04)")
                if "true" in props_lower.get("layoutwrap", "").lower():
                    child_indent = -1
                    for k in range(c + 1, len(controls)):
                        if controls[k]["indent"] <= x["indent"]:
                            break
                        if child_indent < 0:
                            child_indent = controls[k]["indent"]
                        child_props = {kk.lower(): v for kk, v in controls[k]["props"].items()}
                        if (controls[k]["indent"] == child_indent and controls[k]["type"].lower().startswith("groupcontainer@")
                                and "vertical" in child_props.get("layoutdirection", "").lower()):
                            rep.warn(f"{short} :: {x['name']} :: LayoutWrap with vertical child containers; the bar was "
                                     "invisible after pasting (PAPPS-20261007-MAC-01)")
                            break
            if "combobox@" in x["type"].lower() and "searchitems" in props_lower:
                rep.error(f"{short} :: {x['name']} :: SearchItems is not part of the Source Code schema; the paste fails "
                          "with PA2108 (PAPPS-20261024-WIN-01)")
            if "combobox@" in x["type"].lower():
                rep.info(f"{short} :: {x['name']} :: combo box: check DisplayFields after every paste; with a collection "
                         "as Items prefer a checkbox list (PAPPS-20260930-MAC-01)")
    if sources and filters and not matched:
        rep.warn("delegation not checked: no Filter( reads a data source that matches the sources; name the lists with --sources")
    return n_ctl, n_fx
