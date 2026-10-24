"""Small simulator for Power Automate flows from a solution export (local only, no tenant).

Central building block of ppp (origin: project ReiRue, extended in ASUM and Orga-Otto). Covers common action types and
WDL functions and a SharePoint replica for "Send an HTTP request to SharePoint" (REST, odata=verbose or nometadata) with
a schema check from the list definition (default `components/sharepoint/schema.json` of the project).
Project folder = environment variable PPP_PROJEKT (set by `ppp run`), otherwise the current folder. A missing function
raises WdlFehler, a missing action type or connector AssertionError: add it here, not in a project copy.
Export format: runAfter states in both spellings (new designer `SUCCEEDED`, older exports `Succeeded`, often mixed in one
file); header names case-insensitive; SharePoint response according to Accept (verbose/nometadata).
Strict on purpose: function arguments are evaluated completely as in Logic Apps (no short circuit in if/and/or),
`x['a']` on null and property access on text are errors; a reference to an action that has not run yet is an error
(the designer would reject it, PA-20261012-MAC-01).
Limits: parallel branches run one after the other; Scope/If/Foreach are Failed as soon as a direct child failed (Logic
Apps evaluates more finely; a flow must not rely on either variant). Not simulated: other connectors (Get items, Create
item, AI Builder …), Switch, child flows, formatDateTime. `Site` replicates list and field administration for setup flows.

The API (names, messages) stays German so that project generators and tests switch over by changing paths only (Ü-8).
"""
from __future__ import annotations

import base64
import copy
import json
import os
import re
import urllib.parse
import xml.dom.minidom
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

PROJEKT = Path(os.environ.get("PPP_PROJEKT") or Path.cwd())
JETZT = "2026-10-01T08:00:00.0000000Z"


class WdlFehler(Exception):
    pass


class LaufBeendet(Exception):
    """Terminate ends the whole run; result in Lauf.ende."""


# ------------------------------------------------------------------ expressions
TOKEN = re.compile(r"\s*(?:(?P<s>'(?:[^']|'')*')|(?P<n>-?\d+(?:\.\d+)?)|(?P<i>[A-Za-z_][A-Za-z0-9_]*)|(?P<p>\?\[|\?\.|[()\[\],.]))")


def tokens(text):
    pos, out = 0, []
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        m = TOKEN.match(text, pos)
        if not m:
            raise WdlFehler(f"Syntax bei {text[pos:pos + 30]!r}")
        pos = m.end()
        if m.group("s") is not None:
            out.append(("s", m.group("s")[1:-1].replace("''", "'")))
        elif m.group("n") is not None:
            v = m.group("n")
            out.append(("n", float(v) if "." in v else int(v)))
        elif m.group("i") is not None:
            out.append(("i", m.group("i")))
        else:
            out.append(("p", m.group("p")))
    return out


class Parser:
    def __init__(self, text):
        self.t = tokens(text)
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, kind=None, val=None):
        tok = self.peek()
        if kind and tok[0] != kind or val and tok[1] != val:
            raise WdlFehler(f"erwartet {val or kind}, gefunden {tok}")
        self.i += 1
        return tok

    def parse(self):
        e = self.expr()
        if self.i != len(self.t):
            raise WdlFehler(f"Rest nach Ausdruck: {self.t[self.i:]}")
        return e

    def expr(self):
        kind, val = self.take()
        if kind == "s":
            node = ("lit", val)
        elif kind == "n":
            node = ("lit", val)
        elif kind == "i":
            if self.peek() == ("p", "("):
                self.take("p", "(")
                args = []
                if self.peek() != ("p", ")"):
                    args.append(self.expr())
                    while self.peek() == ("p", ","):
                        self.take()
                        args.append(self.expr())
                self.take("p", ")")
                node = ("call", val, args)
            elif val in ("true", "false", "null"):
                node = ("lit", {"true": True, "false": False, "null": None}[val])
            else:
                raise WdlFehler(f"unbekannter Bezeichner {val}")
        else:
            raise WdlFehler(f"unerwartet {val}")
        while self.peek()[1] in ("[", "?[", ".", "?."):
            op = self.take()[1]
            if op in ("[", "?["):
                idx = self.expr()
                self.take("p", "]")
                node = ("idx", node, idx, op == "?[")
            else:
                name = self.take("i")[1]
                node = ("idx", node, ("lit", name), op == "?.")
        return node


def zeit(s):
    if not isinstance(s, str):
        raise WdlFehler(f"Zeitstempel erwartet, gefunden {s!r}")
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)?$", s)
    if not m:
        raise WdlFehler(f"kein ISO-Zeitstempel: {s!r}")
    y, mo, d, h, mi, se = (int(m.group(k)) for k in range(1, 7))
    frac = int((m.group(7) or ".0")[1:].ljust(7, "0")[:7])
    dt = datetime(y, mo, d, h, mi, se, tzinfo=timezone.utc)
    if m.group(8) and m.group(8) != "Z":
        sign = 1 if m.group(8)[0] == "+" else -1
        hh, mm = int(m.group(8)[1:3]), int(m.group(8)[4:6])
        dt = dt.replace(tzinfo=None)
        from datetime import timedelta

        dt = (dt - sign * timedelta(hours=hh, minutes=mm)).replace(tzinfo=timezone.utc)
    return dt, frac


def _iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")


def ticks(s):
    dt, frac = zeit(s)
    basis = datetime(1, 1, 1, tzinfo=timezone.utc)
    delta = dt - basis
    return (delta.days * 86400 + delta.seconds) * 10_000_000 + frac


def to_str(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    if isinstance(v, float) and v.is_integer():
        return str(v)
    return str(v)


def gleich(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or (isinstance(a, bool) and isinstance(b, bool) and a == b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    return a == b


def num(v, name):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise WdlFehler(f"{name}: Zahl erwartet, gefunden {v!r}")
    return v


class Kontext:
    def __init__(self, sim, item_stack=None):
        self.sim = sim
        self.item_stack = item_stack or []


def ev(node, kx: Kontext):
    art = node[0]
    if art == "lit":
        return node[1]
    if art == "idx":
        basis = ev(node[1], kx)
        idx = ev(node[2], kx)
        if basis is None:
            if node[3]:
                return None
            raise WdlFehler(f"Eigenschaft {idx!r} auf null")
        if isinstance(basis, dict):
            if isinstance(idx, str):
                # strict: case matters (Logic Apps may be more tolerant; then this does no harm)
                return basis.get(idx)
            raise WdlFehler("Objektindex muss Text sein")
        if isinstance(basis, list):
            if isinstance(idx, int) and not isinstance(idx, bool):
                if 0 <= idx < len(basis):
                    return basis[idx]
                raise WdlFehler(f"Index {idx} ausserhalb (Länge {len(basis)})")
            raise WdlFehler("Property selection auf Array")
        raise WdlFehler(f"Property selection is not supported on values of type {type(basis).__name__}")
    name, args = node[1], [ev(a, kx) for a in node[2]]
    f = FUNKTIONEN.get(name)
    if f is None:
        raise WdlFehler(f"The template function '{name}' is not defined")
    return f(kx, *args)


def _json(kx, s):
    if not isinstance(s, str):
        raise WdlFehler("json() erwartet Text")
    try:
        return json.loads(s)
    except json.JSONDecodeError as ex:
        raise WdlFehler(f"json(): ungültiges JSON: {ex}") from None


def _int(kx, v):
    if isinstance(v, bool):
        raise WdlFehler("int(bool)")
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str) and re.fullmatch(r"\s*-?\d+\s*", v):
        return int(v)
    raise WdlFehler(f"int(): nicht umwandelbar {v!r}")


def _empty(kx, v):
    if v is None:
        return True
    if isinstance(v, (str, list, dict)):
        return len(v) == 0
    raise WdlFehler(f"empty() auf {type(v).__name__}")


def _length(kx, v):
    if isinstance(v, (str, list)):
        return len(v)
    raise WdlFehler(f"length() auf {v!r}")


def _contains(kx, c, v):
    if isinstance(c, str):
        return to_str(v) in c
    if isinstance(c, list):
        return any(gleich(x, v) for x in c)
    if isinstance(c, dict):
        return any(k.lower() == str(v).lower() for k in c)
    raise WdlFehler("contains() auf ungeeignetem Typ")


def _union(kx, *arrs):
    if all(isinstance(a, list) for a in arrs):
        out = []
        for a in arrs:
            for x in a:
                if not any(gleich(x, y) for y in out):
                    out.append(x)
        return out
    if all(isinstance(a, dict) for a in arrs):
        out = {}
        for a in arrs:
            out.update(a)
        return out
    raise WdlFehler("union(): gemischte Typen")


def _minmax(fn):
    def f(kx, *a):
        werte = a[0] if len(a) == 1 and isinstance(a[0], list) else list(a)
        if not werte:
            raise WdlFehler(f"{fn.__name__}() ohne Werte")
        return fn(num(w, fn.__name__) for w in werte)

    return f


def _vergleich(op):
    def f(kx, a, b):
        if isinstance(a, str) and isinstance(b, str):
            return op(a, b)
        return op(num(a, "Vergleich"), num(b, "Vergleich"))

    return f


def _substring(kx, s, start, laenge=None):
    """As in Power Automate: the start index must be below the text length, also for length 0 (ASUM run 2026-10-08)."""
    if not isinstance(s, str):
        raise WdlFehler("substring() erwartet Text")
    if start < 0 or start >= len(s):
        raise WdlFehler("substring(): 'start index' must be non-negative and less than the length of the string")
    ende = len(s) if laenge is None else start + laenge
    if ende > len(s) or (laenge is not None and laenge < 0):
        raise WdlFehler("substring(): Bereich ausserhalb")
    return s[start:ende]


def _set_property(kx, obj, key, val):
    if not isinstance(obj, dict):
        raise WdlFehler("setProperty() auf Nicht-Objekt")
    o = copy.deepcopy(obj)
    o[key] = val
    return o


def _first(kx, v):
    if isinstance(v, list):
        return v[0] if v else None
    if isinstance(v, str):
        return v[:1]
    if v is None:
        raise WdlFehler("first(null)")
    raise WdlFehler("first() auf ungeeignetem Typ")


def _float(v):
    if isinstance(v, bool):
        raise WdlFehler("float(bool)")
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except ValueError:
        raise WdlFehler(f"float(): nicht umwandelbar {v!r}") from None


def _add_property(o, k, v):
    if not isinstance(o, dict):
        raise WdlFehler("addProperty() auf Nicht-Objekt")
    if k in o:
        raise WdlFehler(f"addProperty(): Eigenschaft {k} existiert bereits")
    o = copy.deepcopy(o)
    o[k] = v
    return o


def _item(kx):
    if not kx.item_stack:
        raise WdlFehler("item() ausserhalb von Query/Select/Foreach")
    return kx.item_stack[-1][1]


def _items(kx, name):
    for n, v in reversed(kx.item_stack):
        if n == name:
            return v
    raise WdlFehler(f"items('{name}') ausserhalb der Schleife")


def _add(kx, a, b):
    return num(a, "add") + num(b, "add")


def _sub(kx, a, b):
    return num(a, "sub") - num(b, "sub")


def _logik(kx, *a):
    for x in a:
        if not isinstance(x, bool):
            raise WdlFehler(f"and/or erwartet Boolean, gefunden {x!r}")
    return a


def _format_number(kx, n, fmt, loc=None):
    """Only the formats '0' and '0.#…' (rounded half up) in locale en-US."""
    num(n, "formatNumber")
    if loc not in (None, "en-US"):
        raise WdlFehler(f"formatNumber: Gebietsschema {loc} nicht nachgebildet")
    d = Decimal(str(n))
    if fmt == "0":
        return str(d.quantize(Decimal("1"), ROUND_HALF_UP))
    m = re.fullmatch(r"0\.(#+)", fmt)
    if not m:
        raise WdlFehler(f"formatNumber: Format {fmt} nicht nachgebildet")
    s = format(d.quantize(Decimal(1).scaleb(-len(m.group(1))), ROUND_HALF_UP), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _actions(kx, name):
    kx.sim.assert_visible(name)
    e = kx.sim._eintrag(name)
    return {"name": name, "status": kx.sim.status.get(name), "outputs": e[1] if e else None}


def _parameters(kx, name):
    if name not in kx.sim.parameter:
        raise WdlFehler(f"Parameter {name} fehlt (im Test Lauf.parameter setzen)")
    return kx.sim.parameter[name]


def _teil(name, vorne):
    def f(kx, c, n):
        if not isinstance(c, (str, list)):
            raise WdlFehler(f"{name}() erwartet Text oder Array")
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise WdlFehler(f"{name}(): Anzahl muss eine ganze Zahl >= 0 sein, gefunden {n!r}")
        return c[:n] if vorne else c[n:]

    return f


def _range(kx, start, anzahl):
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (start, anzahl)) or anzahl < 0:
        raise WdlFehler(f"range(): ganze Zahlen erwartet, gefunden {start!r}, {anzahl!r}")
    return list(range(start, start + anzahl))


def _remove_property(kx, o, k):
    if not isinstance(o, dict):
        raise WdlFehler("removeProperty() auf Nicht-Objekt")
    return {x: copy.deepcopy(v) for x, v in o.items() if x != k}


def _base64_text(kx, s):
    try:
        return base64.b64decode(s, validate=True).decode("utf-8")
    except (ValueError, TypeError):
        raise WdlFehler("base64ToString(): kein gültiges Base64") from None


SCHEMA_TYPEN = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: not isinstance(v, bool) and (isinstance(v, int) or isinstance(v, float) and v.is_integer()),
    "number": lambda v: not isinstance(v, bool) and isinstance(v, (int, float)),
    "null": lambda v: v is None,
}


def schema_pruefen(v, sch, pfad):
    """Parse JSON: type (also a list), required, properties and items, as at run time (null for "string" is an error)."""
    typen = sch.get("type")
    if typen:
        typen = typen if isinstance(typen, list) else [typen]
        if not any(SCHEMA_TYPEN[t](v) for t in typen):
            raise WdlFehler(f"{pfad}: Schema erwartet {'/'.join(typen)}, gefunden {type(v).__name__}")
    if isinstance(v, dict):
        for pflicht in sch.get("required") or []:
            if pflicht not in v:
                raise WdlFehler(f"{pfad}: Pflichtfeld {pflicht} fehlt")
        for k, s in (sch.get("properties") or {}).items():
            if k in v:
                schema_pruefen(v[k], s, f"{pfad}.{k}")
    if isinstance(v, list) and isinstance(sch.get("items"), dict):
        for i, x in enumerate(v):
            schema_pruefen(x, sch["items"], f"{pfad}[{i}]")


FUNKTIONEN = {
    "json": _json,
    "string": lambda kx, v: to_str(v),
    "coalesce": lambda kx, *a: next((x for x in a if x is not None), None),
    "if": lambda kx, c, a, b: (a if c else b) if isinstance(c, bool) else (_ for _ in ()).throw(WdlFehler("if() erwartet Boolean")),
    "equals": lambda kx, a, b: gleich(a, b),
    "not": lambda kx, a: (not a) if isinstance(a, bool) else (_ for _ in ()).throw(WdlFehler("not() erwartet Boolean")),
    "and": lambda kx, *a: all(_logik(kx, *a)),
    "or": lambda kx, *a: any(_logik(kx, *a)),
    "less": _vergleich(lambda a, b: a < b),
    "lessOrEquals": _vergleich(lambda a, b: a <= b),
    "greater": _vergleich(lambda a, b: a > b),
    "greaterOrEquals": _vergleich(lambda a, b: a >= b),
    "int": _int,
    "concat": lambda kx, *a: "".join(to_str(x) for x in a),
    "add": _add,
    "sub": _sub,
    "length": _length,
    "substring": _substring,
    "setProperty": _set_property,
    "join": lambda kx, arr, sep: sep.join(to_str(x) for x in arr) if isinstance(arr, list) else (_ for _ in ()).throw(WdlFehler("join() erwartet Array")),
    "split": lambda kx, s, sep: s.split(sep) if isinstance(s, str) else (_ for _ in ()).throw(WdlFehler("split() erwartet Text")),
    "union": _union,
    "empty": _empty,
    "contains": _contains,
    "createArray": lambda kx, *a: list(a) if a else (_ for _ in ()).throw(WdlFehler("createArray() erwartet mindestens ein Argument")),
    "ticks": lambda kx, s: ticks(s),
    "min": _minmax(min),
    "max": _minmax(max),
    "first": _first,
    "toLower": lambda kx, s: s.lower() if isinstance(s, str) else (_ for _ in ()).throw(WdlFehler("toLower() erwartet Text")),
    "trim": lambda kx, s: s.strip() if isinstance(s, str) else (_ for _ in ()).throw(WdlFehler("trim() erwartet Text")),
    "utcNow": lambda kx: JETZT,
    "float": lambda kx, v: _float(v),
    "addProperty": lambda kx, o, k, v: _add_property(o, k, v),
    "toUpper": lambda kx, s: s.upper() if isinstance(s, str) else (_ for _ in ()).throw(WdlFehler("toUpper() erwartet Text")),
    "guid": lambda kx: "0f8fad5b-d9cb-469f-a165-70867728950e",
    "startsWith": lambda kx, s, t: to_str(s).lower().startswith(to_str(t).lower()),
    "endsWith": lambda kx, s, t: to_str(s).lower().endswith(to_str(t).lower()),
    "replace": lambda kx, s, a, b: s.replace(a, b) if isinstance(s, str) else (_ for _ in ()).throw(WdlFehler("replace() erwartet Text")),
    "last": lambda kx, v: (v[-1] if v else None) if isinstance(v, (list, str)) else (_ for _ in ()).throw(WdlFehler("last()")),
    "mul": lambda kx, a, b: num(a, "mul") * num(b, "mul"),
    "div": lambda kx, a, b: num(a, "div") / num(b, "div") if isinstance(a, float) or isinstance(b, float) else int(num(a, "div") / num(b, "div")),
    "addMinutes": lambda kx, ts, n: _iso(zeit(ts)[0] + timedelta(minutes=num(n, "addMinutes"))),
    "workflow": lambda kx: {"run": {"name": kx.sim.lauf}},
    "trigger": lambda kx: {"startTime": JETZT, "outputs": kx.sim.trigger_outputs},
    "triggerBody": lambda kx: kx.sim.trigger_outputs["body"],
    "triggerOutputs": lambda kx: kx.sim.trigger_outputs,
    "item": _item,
    "items": _items,
    "variables": lambda kx, n: copy.deepcopy(kx.sim.vars[n]) if n in kx.sim.vars else (_ for _ in ()).throw(WdlFehler(f"Variable {n} fehlt")),
    "outputs": lambda kx, n: kx.sim.ausgabe(n, kx, "outputs"),
    "body": lambda kx, n: kx.sim.ausgabe(n, kx, "body"),
    "result": lambda kx, n: kx.sim.result(n),
    "actions": _actions,
    "parameters": _parameters,
    "formatNumber": _format_number,
    "indexOf": lambda kx, s, t: to_str(s).lower().find(to_str(t).lower()),
    "take": _teil("take", True),
    "skip": _teil("skip", False),
    "range": _range,
    "removeProperty": _remove_property,
    "uriComponent": lambda kx, s: urllib.parse.quote(to_str(s), safe=""),
    "uriComponentToString": lambda kx, s: urllib.parse.unquote(to_str(s)),
    "decodeUriComponent": lambda kx, s: urllib.parse.unquote(to_str(s)),
    "base64ToString": _base64_text,
    "decodeBase64": _base64_text,
}


def werte(v, kx):
    """Evaluate action inputs: '@…' typed, '@{…}' interpolated, objects and lists recursively."""
    if isinstance(v, dict):
        return {k: werte(x, kx) for k, x in v.items()}
    if isinstance(v, list):
        return [werte(x, kx) for x in v]
    if not isinstance(v, str) or "@" not in v:
        return v
    if v.startswith("@@"):
        return v[1:]
    if v.startswith("@") and not v.startswith("@{"):
        return ev(Parser(v[1:]).parse(), kx)
    out, i = [], 0
    while True:
        k = v.find("@{", i)
        if k < 0:
            out.append(v[i:])
            break
        out.append(v[i:k])
        d, q, m = 0, False, k + 2
        while True:
            c = v[m]
            if q:
                if c == "'":
                    if v[m + 1:m + 2] == "'":
                        m += 2
                        continue
                    q = False
            elif c == "'":
                q = True
            elif c == "{":
                d += 1
            elif c == "}":
                if d == 0:
                    break
                d -= 1
            m += 1
        out.append(to_str(ev(Parser(v[k + 2:m]).parse(), kx)))
        i = m + 1
    return "".join(out)


def bedingung(b, kx):
    if isinstance(b, str):
        return werte(b, kx)
    ((op, arg),) = b.items()
    if op == "and":
        return all([bedingung(x, kx) for x in arg])
    if op == "or":
        return any([bedingung(x, kx) for x in arg])
    if op == "not":
        return not bedingung(arg, kx)
    a, c = werte(arg[0], kx), werte(arg[1], kx)
    return FUNKTIONEN[op](kx, a, c)


# ------------------------------------------------------------------ SharePoint replica
class SharePoint:
    def __init__(self, definition_pfad=None):
        if definition_pfad is None:
            definition_pfad = PROJEKT / "components/sharepoint/schema.json"
            if not definition_pfad.exists():  # project not yet moved to the ppp structure
                definition_pfad = PROJEKT / "import-export/listen_definition.json"
        d = json.loads(Path(definition_pfad).read_text(encoding="utf-8"))
        self.schema, self.listen = {}, {}
        for liste in d["listen"]:
            felder = {"Title": {"typ": "Text"}}
            for f in liste["felder"]:
                x = xml.dom.minidom.parseString(f["schemaXml"]).documentElement
                felder[f["name"]] = {
                    "typ": x.getAttribute("Type"),
                    "choices": [c.firstChild.data for c in x.getElementsByTagName("CHOICE")],
                }
            name = liste["titel"]
            self.schema[name] = {
                "felder": felder,
                "unique": bool((liste.get("titelFeld") or {}).get("EnforceUniqueValues")),
                "typ": "SP.Data." + name.replace("_", "_x005f_") + "ListItem",
            }
            self.listen[name] = {}
        self.naechste = {n: 1 for n in self.listen}
        self.protokoll = []
        self.vor_merge = None  # hook for conflict tests: fn(liste, id)
        self.stoerung = None  # hook for error paths: fn(methode, uri) -> (code, body) | None
        self.jetzt = JETZT

    def neu(self, liste, felder):
        i = self.naechste[liste]
        self.naechste[liste] += 1
        self.listen[liste][i] = {"Id": i, "_v": 1, "Created": self.jetzt, **felder}
        return i

    def _pruefe(self, liste, body):
        sch = self.schema[liste]
        if (body.get("__metadata") or {}).get("type") != sch["typ"]:
            return 400, f"__metadata.type {body.get('__metadata')} statt {sch['typ']}"
        for k, v in body.items():
            if k == "__metadata":
                continue
            f = sch["felder"].get(k)
            if f is None:
                return 400, f"Feld {k} existiert nicht in {liste}"
            t = f["typ"]
            if v is None:
                continue
            if t == "Choice" and v not in f["choices"]:
                return 400, f"{liste}.{k}: Wert {v!r} nicht in Auswahl"
            if t == "Boolean" and not isinstance(v, bool):
                return 400, f"{liste}.{k}: Boolean erwartet, {v!r}"
            if t == "Number" and (isinstance(v, bool) or not isinstance(v, (int, float))):
                return 400, f"{liste}.{k}: Zahl erwartet, {v!r}"
            if t == "DateTime":
                try:
                    zeit(v)
                except WdlFehler:
                    return 400, f"{liste}.{k}: Datum erwartet, {v!r}"
            if t in ("Text", "Note") and not isinstance(v, str):
                return 400, f"{liste}.{k}: Text erwartet, {v!r}"
            if t == "Text" and len(v) > 255:
                return 400, f"{liste}.{k}: Text > 255 Zeichen"
        return None

    def _aus(self, liste, row, select=None, verbose=True):
        # SharePoint returns the item ID as Id and ID
        o = {k: v for k, v in row.items() if k != "_v"}
        o["ID"] = row["Id"]
        if select:
            o = {k: o.get(k) for k in select}
        if verbose:
            o["__metadata"] = {"type": self.schema[liste]["typ"], "etag": f'"{row["_v"]}"'}
        return o

    def _filter(self, row, ausdruck):
        for teil in re.split(r"\s+and\s+", ausdruck.strip()):
            m = re.fullmatch(r"(\w+)\s+(eq|ne|le|lt|ge|gt)\s+('(?:[^']|'')*'|-?\d+(?:\.\d+)?)", teil.strip())
            if not m:
                raise AssertionError(f"Filter nicht nachgebildet: {teil}")
            f, op, w = m.groups()
            w = w[1:-1].replace("''", "'") if w.startswith("'") else float(w)
            v = row["Id"] if f == "ID" else row.get(f)
            if isinstance(v, bool):
                v = 1.0 if v else 0.0
            if isinstance(w, float) and v is not None and not isinstance(v, str):
                v = float(v)
            if isinstance(w, str) and v is None:
                v = ""
            ok = {"eq": lambda: v == w, "ne": lambda: v != w, "le": lambda: v is not None and v <= w,
                  "lt": lambda: v is not None and v < w, "ge": lambda: v is not None and v >= w,
                  "gt": lambda: v is not None and v > w}[op]()
            if not ok:
                return False
        return True

    def anfrage(self, methode, uri, kopf, body):
        self.protokoll.append((methode, uri))
        if self.stoerung:
            s = self.stoerung(methode, uri)
            if s:
                return s
        m = re.fullmatch(r"_api/web/lists/getbytitle\('([^']+)'\)/items(?:\((\d+)\))?(?:\?(.*))?", uri)
        if not m:
            return 400, {"error": f"URI nicht nachgebildet: {uri}"}
        liste, iid, query = m.group(1), m.group(2), m.group(3) or ""
        if liste not in self.listen:
            return 404, {"error": "Liste fehlt"}
        q = dict(p.split("=", 1) for p in query.split("&") if p)
        select = q.get("$select", "").split(",") if q.get("$select") else None
        daten = self.listen[liste]
        # header names are case-insensitive; the response form follows the Accept header
        kopf = {k.lower(): v for k, v in (kopf or {}).items()}
        accept = str(kopf.get("accept", "")).replace(" ", "").lower()
        if "odata=verbose" in accept:
            verbose = True
        elif "odata=nometadata" in accept:
            verbose = False
        else:
            return 400, {"error": f"Accept {accept!r} nicht nachgebildet (odata=verbose oder odata=nometadata)"}
        if methode == "GET":
            if iid:
                if int(iid) not in daten:
                    return 404, {"error": "Element fehlt"}
                o = self._aus(liste, daten[int(iid)], select, verbose)
                return 200, {"d": o} if verbose else o
            rows = [r for r in daten.values() if "$filter" not in q or self._filter(r, q["$filter"])]
            werte_ = [self._aus(liste, r, select, verbose) for r in rows][: int(q.get("$top", 100))]
            return 200, {"d": {"results": werte_}} if verbose else {"value": werte_}
        if methode != "POST":
            return 400, {"error": "Methode"}
        if str(kopf.get("content-type", "")).replace(" ", "").lower() != "application/json;odata=verbose":
            return 400, {"error": "Content-Type fehlt"}
        try:
            b = json.loads(body) if isinstance(body, str) else None
        except json.JSONDecodeError:
            return 400, {"error": "Invalid JSON"}
        if not isinstance(b, dict):
            return 400, {"error": "Body muss JSON-Text sein"}
        fehler = self._pruefe(liste, b)
        if fehler:
            return fehler[0], {"error": fehler[1]}
        felder = {k: v for k, v in b.items() if k != "__metadata"}
        if self.schema[liste]["unique"] and "Title" in felder:
            for r in daten.values():
                if r.get("Title") == felder["Title"] and (not iid or r["Id"] != int(iid)):
                    return 400, {"error": f"Title nicht eindeutig: {felder['Title']}"}
        if iid:
            if kopf.get("x-http-method") != "MERGE":
                return 400, {"error": "MERGE erwartet"}
            if int(iid) not in daten:
                return 404, {"error": "Element fehlt"}
            if self.vor_merge:
                self.vor_merge(liste, int(iid))
            row = daten[int(iid)]
            im = kopf.get("if-match")
            if im is None:
                return 400, {"error": "IF-MATCH fehlt"}
            if im != "*" and im != f'"{row["_v"]}"':
                return 412, {"error": "The request ETag value does not match the object's ETag value"}
            row.update(felder)
            row["_v"] += 1
            return 204, None
        i = self.neu(liste, felder)
        o = self._aus(liste, daten[i], verbose=verbose)
        return 201, {"d": o} if verbose else o


class Site(SharePoint):
    """SharePoint with list and field administration, for setup flows (origin: ASUM tests/flows/test_asum_setup.py).

    Lists exist only after POST _api/web/lists; fields after createfieldasxml; choice values and the Title index can be
    read and raised with MERGE. Items go through SharePoint. `vorhanden`: list -> {"basis", "felder"};
    `auswahl`: (list, field) -> choice values.
    """

    def __init__(self, definition_pfad=None):
        super().__init__(definition_pfad)
        self.vorhanden = {}
        self.auswahl = {}

    def _pruefe(self, liste, body):
        for k in body:
            if k not in ("__metadata", "Title") and k not in self.vorhanden[liste]["felder"]:
                return 400, f"Feld {k} existiert (noch) nicht in {liste}"
        return super()._pruefe(liste, body)

    def anfrage(self, methode, uri, kopf, body):
        self.protokoll.append((methode, uri))
        if self.stoerung:
            s = self.stoerung(methode, uri)
            if s:
                return s
        kopf_l = {k.lower(): v for k, v in (kopf or {}).items()}
        if uri == "_api/web/lists?$select=Title&$top=5000" and methode == "GET":
            return 200, {"d": {"results": [{"Title": t} for t in self.vorhanden]}}
        if uri == "_api/web/lists" and methode == "POST":
            b = json.loads(body)
            if b.get("__metadata", {}).get("type") != "SP.List" or b.get("BaseTemplate") not in (100, 101):
                return 400, {"error": f"Liste: unerwarteter Body {b}"}
            if b["Title"] in self.vorhanden:
                return 409, {"error": "Liste existiert"}
            self.vorhanden[b["Title"]] = {"basis": b["BaseTemplate"], "felder": {
                "Title": {"InternalName": "Title", "Indexed": False, "EnforceUniqueValues": False}}}
            if b["Title"] not in self.listen:  # list unknown to the definition: items without schema check
                self.listen[b["Title"]] = {}
                self.naechste[b["Title"]] = 1
                self.schema[b["Title"]] = {"felder": {"Title": {"typ": "Text"}}, "unique": False,
                                           "typ": "SP.Data." + b["Title"].replace("_", "_x005f_") + "ListItem"}
            return 201, {"d": {"Title": b["Title"]}}
        m = re.fullmatch(r"_api/web/lists/getbytitle\('([^']+)'\)(.*)", uri)
        if not m:
            return 400, {"error": f"URI nicht nachgebildet: {uri}"}
        liste, rest = m.groups()
        if liste not in self.vorhanden:
            return 404, {"error": f"Liste {liste} fehlt"}
        felder = self.vorhanden[liste]["felder"]
        if rest == "?$select=ListItemEntityTypeFullName" and methode == "GET":
            return 200, {"d": {"ListItemEntityTypeFullName": self.schema[liste]["typ"]}}
        if rest == "/fields?$select=InternalName,Indexed,EnforceUniqueValues&$top=5000" and methode == "GET":
            return 200, {"d": {"results": list(copy.deepcopy(felder).values())}}
        if rest == "/fields/createfieldasxml" and methode == "POST":
            p = json.loads(body)["parameters"]
            if p.get("__metadata", {}).get("type") != "SP.XmlSchemaFieldCreationInformation":
                return 400, {"error": "createfieldasxml: __metadata.type"}
            x = xml.dom.minidom.parseString(p["SchemaXml"]).documentElement
            n = x.getAttribute("Name")
            if n in felder:
                return 409, {"error": f"Feld {liste}.{n} existiert"}
            felder[n] = {"InternalName": n, "Indexed": x.getAttribute("Indexed") == "TRUE",
                         "EnforceUniqueValues": x.getAttribute("EnforceUniqueValues") == "TRUE"}
            if x.getAttribute("Type") in ("Choice", "MultiChoice"):
                self.auswahl[(liste, n)] = [c.firstChild.data for c in x.getElementsByTagName("CHOICE")]
            return 201, {"d": {"InternalName": n}}
        mf = re.fullmatch(r"/fields/getbyinternalnameortitle\('([^']+)'\)(\?\$select=Choices)?", rest)
        if mf and mf.group(1) != "Title":
            n = mf.group(1)
            if n not in felder:
                return 404, {"error": f"Feld {liste}.{n} fehlt"}
            if methode == "GET" and mf.group(2):
                ch = self.auswahl.get((liste, n))
                return 200, {"d": {"Choices": {"__metadata": {"type": "Collection(Edm.String)"}, "results": list(ch)}} if ch is not None else {}}
            if methode == "POST" and not mf.group(2):
                if kopf_l.get("x-http-method") != "MERGE" or kopf_l.get("if-match") != "*":
                    return 400, {"error": "MERGE mit IF-MATCH * erwartet"}
                b = json.loads(body)
                alt = self.auswahl.get((liste, n), [])
                if b.get("__metadata", {}).get("type") != "SP.FieldChoice" or b["Choices"]["results"][:len(alt)] != alt:
                    return 400, {"error": "Auswahlwerte: Typ falsch oder bestehende verändert"}
                self.auswahl[(liste, n)] = list(b["Choices"]["results"])
                return 204, None
        if rest == "/fields/getbyinternalnameortitle('Title')" and methode == "POST":
            if kopf_l.get("x-http-method") != "MERGE" or kopf_l.get("if-match") != "*":
                return 400, {"error": "MERGE mit IF-MATCH * erwartet"}
            b = json.loads(body)
            felder["Title"].update({"Indexed": b["Indexed"], "EnforceUniqueValues": b["EnforceUniqueValues"]})
            self.schema[liste]["unique"] = b["EnforceUniqueValues"]
            return 204, None
        if rest.startswith("/items"):
            self.protokoll.pop()  # the base class logs itself
            return super().anfrage(methode, uri, kopf, body)
        return 400, {"error": f"URI nicht nachgebildet: {uri}"}


# ------------------------------------------------------------------ flow run
def _zweige(a):
    """Nested blocks of an action: actions, else, cases, default."""
    teile = [a.get("actions"), (a.get("else") or {}).get("actions"), (a.get("default") or {}).get("actions")]
    teile += [(c or {}).get("actions") for c in (a.get("cases") or {}).values()]
    return [t for t in teile if t]


class Lauf:
    def __init__(self, definition, sp: SharePoint, lauf, auftrag_text, email):
        self.defn = definition["properties"]["definition"]
        self.sp = sp
        self.lauf = lauf
        self.trigger_outputs = {"headers": {"x-ms-user-email": email}, "body": {"text": auftrag_text}}
        self.vars = {}
        self.global_out = {}
        self.status = {}
        self.fehler = {}
        self.antwort = None
        self.ende = None  # Terminate: {"runStatus": …, "runError": …}
        self.parameter = {}  # parameters('<display name> (<schema name>)') -> value, set in the test
        self.scopes = {}
        self.iter_stack = []  # per loop level: dict name -> (status, outputs)

    # Ausgaben
    def _eintrag(self, name):
        for ebene in reversed(self.iter_stack):
            if name in ebene:
                return ebene[name]
        return self.global_out.get(name)

    def ausgabe(self, name, kx, art):
        self.assert_visible(name)
        e = self._eintrag(name)
        if e is None:
            return None
        typ, out = e
        if typ in ("Query", "Select", "ParseJson"):
            return out if art == "body" else {"body": out}
        if typ == "OpenApiConnection":
            return out["body"] if art == "body" else out
        return out

    def result(self, name):
        self.assert_visible(name)
        return [{"name": n, "status": s} for n, s in self.scopes.get(name, [])]

    def assert_visible(self, name):
        """Only actions that have run (or were skipped) can be referenced (origin: Orga-Otto)."""
        if name not in self.alle_namen:
            raise WdlFehler(f"unbekannte Aktion {name}")
        if name not in self.status:
            raise WdlFehler(f"Aktion {name} noch nicht ausgewertet")

    def _set(self, name, typ, out, status):
        ziel = self.iter_stack[-1] if self.iter_stack else self.global_out
        if out is not None or typ in ("Compose",):
            ziel[name] = (typ, out)
        self.status[name] = status

    def start(self):
        self.alle_namen = set()

        def sammle(acts):
            for n, a in acts.items():
                self.alle_namen.add(n)
                for teil in _zweige(a):
                    sammle(teil)

        sammle(self.defn["actions"])
        try:
            self.ebene(self.defn["actions"], Kontext(self))
        except LaufBeendet:
            pass
        return self

    def ebene(self, acts, kx):
        erledigt = {}
        offen = dict(acts)
        while offen:
            fort = False
            for n, a in list(offen.items()):
                ra = a.get("runAfter") or {}
                if all(d in erledigt for d in ra):
                    del offen[n]
                    fort = True
                    # new designer: SUCCEEDED/FAILED/SKIPPED/TIMEDOUT, older exports Succeeded/…; Logic Apps compares
                    # case-insensitively (otherwise every action would be skipped silently)
                    if all(erledigt[d].upper() in {x.upper() for x in s} for d, s in ra.items()):
                        st = self.aktion(n, a, kx)
                    else:
                        st = "Skipped"
                        self.status[n] = st
                        self._skip_children(a)
                    erledigt[n] = st
            if not fort:
                raise AssertionError(f"runAfter-Zyklus/unauflösbar: {list(offen)}")
        return erledigt

    def _skip_children(self, action):
        """Nested actions of a skipped action count as skipped (origin: Orga-Otto)."""
        for teil in _zweige(action):
            for name, child in teil.items():
                self.status[name] = "Skipped"
                self._skip_children(child)

    def aktion(self, n, a, kx):
        typ = a["type"]
        try:
            if typ == "InitializeVariable":
                v = a["inputs"]["variables"][0]
                self.vars[v["name"]] = werte(v.get("value"), kx)
                st = "Succeeded"
            elif typ == "SetVariable":
                self.vars[a["inputs"]["name"]] = werte(a["inputs"]["value"], kx)
                st = "Succeeded"
            elif typ == "AppendToArrayVariable":
                self.vars[a["inputs"]["name"]].append(werte(a["inputs"]["value"], kx))
                st = "Succeeded"
            elif typ == "IncrementVariable":
                vn = a["inputs"]["name"]
                self.vars[vn] = num(self.vars[vn], n) + num(werte(a["inputs"].get("value", 1), kx), n)
                st = "Succeeded"
            elif typ == "ParseJson":
                inhalt = werte(a["inputs"]["content"], kx)
                if isinstance(inhalt, str):
                    inhalt = _json(kx, inhalt)
                schema_pruefen(inhalt, a["inputs"].get("schema") or {}, n)
                self._set(n, typ, inhalt, "Succeeded")
                st = "Succeeded"
            elif typ == "Terminate":
                self.ende = {"runStatus": a["inputs"]["runStatus"], "runError": werte(a["inputs"].get("runError"), kx)}
                self.status[n] = "Succeeded"
                raise LaufBeendet
            elif typ == "Compose":
                self._set(n, typ, werte(a["inputs"], kx), "Succeeded")
                st = "Succeeded"
            elif typ in ("Query", "Select"):
                von = werte(a["inputs"]["from"], kx)
                if not isinstance(von, list):
                    raise WdlFehler(f"{n}: from ist kein Array ({type(von).__name__})")
                out = []
                for it in von:
                    k2 = Kontext(self, kx.item_stack + [(n, it)])
                    if typ == "Query":
                        w = werte(a["inputs"]["where"], k2)
                        if not isinstance(w, bool):
                            raise WdlFehler(f"{n}: where liefert kein Boolean")
                        if w:
                            out.append(it)
                    else:
                        out.append(werte(a["inputs"]["select"], k2))
                self._set(n, typ, out, "Succeeded")
                st = "Succeeded"
            elif typ == "OpenApiConnection":
                host = a["inputs"].get("host") or {}
                api = str(host.get("apiId", "")).split("/")[-1]
                if (api, host.get("operationId")) != ("shared_sharepointonline", "HttpRequest"):
                    raise AssertionError(f"{n}: Connector {api}/{host.get('operationId')} nicht nachgebildet")
                p = werte(a["inputs"]["parameters"], kx)
                code, body = self.sp.anfrage(p["parameters/method"], p["parameters/uri"], p.get("parameters/headers") or {}, p.get("parameters/body"))
                st = "Succeeded" if 200 <= code < 300 else "Failed"
                if st == "Failed":
                    self.fehler[n] = (code, body)
                self._set(n, typ, {"statusCode": code, "body": body, "headers": {}}, st)
            elif typ == "If":
                if bedingung(a["expression"], kx):
                    zweig, anderer = a.get("actions") or {}, (a.get("else") or {}).get("actions") or {}
                else:
                    zweig, anderer = (a.get("else") or {}).get("actions") or {}, a.get("actions") or {}
                for name, child in anderer.items():  # the branch not taken is Skipped (origin: Orga-Otto)
                    self.status[name] = "Skipped"
                    self._skip_children(child)
                res = self.ebene(zweig, kx)
                st = "Failed" if "Failed" in res.values() else "Succeeded"
                self.scopes[n] = list(res.items())
            elif typ == "Scope":
                res = self.ebene(a["actions"], kx)
                st = "Failed" if "Failed" in res.values() else "Succeeded"
                self.scopes[n] = list(res.items())
            elif typ == "Foreach":
                von = werte(a["foreach"], kx)
                if not isinstance(von, list):
                    raise WdlFehler(f"{n}: foreach ist kein Array")
                st = "Succeeded"
                for it in von:
                    self.iter_stack.append({})
                    try:
                        res = self.ebene(a["actions"], Kontext(self, kx.item_stack + [(n, it)]))
                    finally:
                        self.iter_stack.pop()
                    if "Failed" in res.values():
                        st = "Failed"
            elif typ == "Response":
                self.antwort = werte(a["inputs"]["body"], kx)
                st = "Succeeded"
            else:
                raise AssertionError(f"Aktionstyp {typ} nicht nachgebildet")
        except WdlFehler as ex:
            self.fehler[n] = str(ex)
            st = "Failed"
        self.status[n] = st
        return st
