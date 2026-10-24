"""Action references must lie on a runAfter or enclosing-scope path.

Origin: project Orga-Otto (tests/flows/pruefe_referenzpfade.py), taken over 2026-10-13. Finds references to actions
that are no transitive runAfter predecessor in the reachable scope path; the designer rejects them on save with
InvalidTemplate (lesson PA-20261012-MAC-01).
"""
from __future__ import annotations

import re

from .flows import CHILD_KEYS, own_part, strings

REF = re.compile(r"(?<![\w])(?:outputs|body|actions|result)\(\s*'([^']+)'\s*\)", re.I)


def _children(action: dict):
    for key in CHILD_KEYS:
        value = action.get(key)
        if not isinstance(value, dict):
            continue
        if key == "actions":
            yield value
        elif key == "cases":
            for case in value.values():
                if isinstance(case, dict):
                    yield case.get("actions", {})
        else:
            yield value.get("actions", {})


def check(flow: dict) -> tuple[list[str], int, str | None]:
    """Findings, number of actions, and a note if the top level has not exactly one start action."""
    root = flow["properties"]["definition"]["actions"]
    findings: list[str] = []
    nodes: dict = {}
    parents: dict = {}
    siblings: dict = {}

    def inventory(acts, parent=None):
        for name, action in acts.items():
            if name in nodes:
                findings.append(f"duplicate action: {name}")
            nodes[name] = action
            parents[name] = parent
            siblings[name] = acts
            for sub in _children(action):
                inventory(sub, name)

    inventory(root)
    roots = [name for name, act in root.items() if not act.get("runAfter")]
    root_note = f"start actions at top level: {len(roots)} instead of 1: {', '.join(roots)}" if len(roots) != 1 else None

    def descendants(name):
        found = {name}
        for sub in _children(nodes[name]):
            for child in sub:
                found |= descendants(child)
        return found

    def before(name, seen=None):
        seen = set() if seen is None else seen
        for dep in nodes[name].get("runAfter", {}) or {}:
            if dep not in siblings[name]:
                findings.append(f"{name}: runAfter {dep} is not a sibling")
                continue
            if dep in seen:
                continue
            seen.add(dep)
            seen.update(descendants(dep))
            before(dep, seen)
        return seen

    for name, act in nodes.items():
        visible = before(name)
        ancestor = parents[name]
        while ancestor:
            visible.add(ancestor)
            visible |= before(ancestor)
            ancestor = parents[ancestor]
        for text in strings(own_part(act)):
            for ref in REF.findall(text):
                if ref not in nodes:
                    findings.append(f"{name} -> {ref}: action missing")
                elif ref not in visible:
                    findings.append(f"{name} -> {ref}: no reference path")
    return findings, len(nodes), root_note
