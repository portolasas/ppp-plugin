"""Power Fx notation: en-US (source, YAML) to de-DE (formula bar, App.Formulas).

Central building block of ppp; same result as PPP-CANVAS (PowerShell), byte-identical on an App.Formulas with
20,000 characters. Rule: outside strings and 'identifiers' first `;` to `;;`, then `,` to `;`, then a decimal point
between digits to `,`. Comments (// …) stay unchanged. The API stays German (Ü-8).
"""
from __future__ import annotations


def nach_de(formel: str) -> str:
    out, i, n = [], 0, len(formel)
    while i < n:
        c = formel[i]
        if c == '"':                                   # string, "" = escaped quote
            j = i + 1
            while j < n:
                if formel[j] == '"' and j + 1 < n and formel[j + 1] == '"':
                    j += 2
                    continue
                if formel[j] == '"':
                    break
                j += 1
            out.append(formel[i:j + 1])
            i = j + 1
        elif c == "'":                                 # identifier in single quotes
            j = formel.index("'", i + 1)
            out.append(formel[i:j + 1])
            i = j + 1
        elif formel.startswith("//", i):               # line comment
            j = formel.find("\n", i)
            j = n if j < 0 else j
            out.append(formel[i:j])
            i = j
        elif c == ";":
            out.append(";;")
            i += 1
        elif c == ",":
            out.append(";")
            i += 1
        elif c == "." and 0 < i < n - 1 and formel[i - 1].isdigit() and formel[i + 1].isdigit():
            out.append(",")
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def pruefe_klammern(formel: str) -> str | None:
    """Simple check: brackets and quotes balanced (outside strings)."""
    stapel, i, n = [], 0, len(formel)
    paare = {")": "(", "]": "[", "}": "{"}
    while i < n:
        c = formel[i]
        if c == '"':
            j = i + 1
            while j < n and not (formel[j] == '"' and not (j + 1 < n and formel[j + 1] == '"')):
                j += 2 if formel[j] == '"' else 1
            if j >= n:
                return "Zeichenkette nicht geschlossen"
            i = j + 1
            continue
        if c == "'":
            j = formel.find("'", i + 1)
            if j < 0:
                return "Bezeichner nicht geschlossen"
            i = j + 1
            continue
        if c in "([{":
            stapel.append(c)
        elif c in ")]}":
            if not stapel or stapel.pop() != paare[c]:
                return f"Klammer {c} an Position {i} passt nicht"
        i += 1
    return f"offene Klammern: {''.join(stapel)}" if stapel else None
