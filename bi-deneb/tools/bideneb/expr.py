"""Vega expressions and the walk through a specification: which fields, functions and colours a spec uses."""
import json
import re

EXPR_KEYS = {"signal", "expr", "update", "init", "test", "calculate", "labelExpr", "filter"}
TOKEN = re.compile(r"""
    (?P<str>'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")
  | (?P<num>\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+)
  | (?P<id>[A-Za-z_$][\w$]*)
  | (?P<op>===|!==|==|!=|<=|>=|&&|\|\||[-+*/%<>!?:.,()\[\]{}=&|^~])
  | (?P<ws>\s+)
""", re.X)
COLOR = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b|rgba?\([^)]*\)")
ROW_OBJECTS = {"datum", "parent"}


def strip_comments(text: str) -> str:
    """JSONC to JSON: // and /* */ comments and trailing commas outside strings removed."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1
                continue
            out.append(c)
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def loads(text: str):
    """JSON or JSONC (Deneb accepts comments in a specification)."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(strip_comments(text))


def tokens(expr: str) -> list[tuple[str, str, int, int]]:
    """(kind, text, start, end) without whitespace."""
    out, pos = [], 0
    while pos < len(expr):
        m = TOKEN.match(expr, pos)
        if not m:
            out.append(("op", expr[pos], pos, pos + 1))
            pos += 1
            continue
        if m.lastgroup != "ws":
            out.append((m.lastgroup, m.group(), m.start(), m.end()))
        pos = m.end()
    return out


def unquote(s: str) -> str:
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s[1:-1])


def quote(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def analyse(expr: str) -> dict:
    """fields: names read from datum/parent; calls: function names; strings: string literals; ids: free names."""
    toks = [(k, t) for k, t, _, _ in tokens(expr)]
    fields, calls, strings, ids = [], [], [], []
    for i, (kind, text) in enumerate(toks):
        prev = toks[i - 1] if i else ("", "")
        nxt = toks[i + 1] if i + 1 < len(toks) else ("", "")
        if kind == "str":
            strings.append(unquote(text))
        elif kind == "id":
            if prev == ("op", "."):
                continue
            if nxt == ("op", "("):
                calls.append(text)
            elif text in ROW_OBJECTS:
                if nxt == ("op", ".") and i + 2 < len(toks) and toks[i + 2][0] == "id":
                    fields.append(toks[i + 2][1])
                elif nxt == ("op", "[") and i + 3 < len(toks) and toks[i + 2][0] == "str" and toks[i + 3] == ("op", "]"):
                    fields.append(unquote(toks[i + 2][1]))
            else:
                ids.append(text)
    return {"fields": fields, "calls": calls, "strings": strings, "ids": ids}


def rewrite_calls(expr: str, names: set, handler) -> str:
    """Replace every call name(args) with name in names by handler(name, [argument sources]); None keeps the call."""
    toks = tokens(expr)
    for i, (kind, text, start, _) in enumerate(toks):
        if kind != "id" or text not in names:
            continue
        if i and toks[i - 1][1] == ".":
            continue
        if i + 1 >= len(toks) or toks[i + 1][1] != "(":
            continue
        depth, args, arg_start, j = 0, [], toks[i + 1][3], i + 1
        while j < len(toks):
            t = toks[j][1]
            if toks[j][0] == "op" and t in "([{":
                depth += 1
            elif toks[j][0] == "op" and t in ")]}":
                depth -= 1
                if depth == 0:
                    last = expr[arg_start:toks[j][2]].strip()
                    if last:
                        args.append(last)
                    break
            elif toks[j][0] == "op" and t == "," and depth == 1:
                args.append(expr[arg_start:toks[j][2]].strip())
                arg_start = toks[j][3]
            j += 1
        else:
            return expr
        args = [rewrite_calls(a, names, handler) for a in args]
        repl = handler(text, args)
        if repl is None:
            repl = f"{text}({', '.join(args)})"
        return expr[:start] + repl + rewrite_calls(expr[toks[j][3]:], names, handler)
    return expr


def walk(node, path=()):
    """Every (path, key, value) of a JSON tree, depth first; path is a tuple of keys and indexes."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield path, k, v
            yield from walk(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, path + (i,))


def expressions(spec) -> list[tuple[tuple, str]]:
    """(path, expression text) for every expression string in a Vega or Vega-Lite specification."""
    return [(path + (key,), value) for path, key, value in walk(spec)
            if key in EXPR_KEYS and isinstance(value, str)]


def map_expressions(node, fn):
    """A copy of the tree with fn applied to every expression string."""
    if isinstance(node, dict):
        return {k: (fn(v) if k in EXPR_KEYS and isinstance(v, str) else map_expressions(v, fn)) for k, v in node.items()}
    if isinstance(node, list):
        return [map_expressions(v, fn) for v in node]
    return node


def show(path: tuple) -> str:
    out = ""
    for p in path:
        out += f"[{p}]" if isinstance(p, int) else (("." if out else "") + str(p))
    return out or "(root)"


def colors_in(value: str) -> list[str]:
    return COLOR.findall(value)
