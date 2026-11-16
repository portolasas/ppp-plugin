"""Invented rows for the preview. Never real data: values are random, names are generic or given in the brief."""
import datetime as dt
import random

SCENARIOS = ("typical", "stress", "few")
LONG = ["Sehr lange Bezeichnung mit Zusatz und Nummer", "Übergreifende Qualitätsprüfung Standort Süd",
        "Kurz", "Abfüllung und Verpackung Linie 3 (Nachtschicht)", "Größenänderung ÄÖÜ ß", "Mittel lang benannt"]
ANCHOR = dt.date(2026, 11, 1)


def categories(f, scenario: str, given: dict, count: int | None = None) -> list[str]:
    if f.key in given or f.display in given:
        vals = [str(v) for v in (given.get(f.key) or given.get(f.display))]
        if scenario == "few":
            return vals[:2]
        if scenario == "stress" and vals:
            more = max(0, (count or 14) - len(vals))
            return vals + [f"{vals[i % len(vals)]} {i + 2} – {LONG[i % len(LONG)]}" if i % 2 else f"{vals[i % len(vals)]} {i + 2}"
                           for i in range(more)]
        return vals
    n = count or {"typical": 6, "stress": 14, "few": 2}[scenario]
    out = [f"{f.label} {chr(65 + i % 26)}{'' if i < 26 else i // 26}" for i in range(n)]
    if scenario == "stress":
        out = [f"{o} {LONG[i % len(LONG)]}" if i % 3 == 0 else o for i, o in enumerate(out)]
    return out


def months(scenario: str, count: int | None = None) -> list[str]:
    n = count or {"typical": 12, "stress": 36, "few": 2}[scenario]
    out, y, m = [], ANCHOR.year, ANCHOR.month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}-01T00:00:00")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def days(scenario: str, count: int | None = None) -> list[str]:
    n = count or {"typical": 30, "stress": 120, "few": 3}[scenario]
    return [(ANCHOR - dt.timedelta(days=n - 1 - i)).isoformat() + "T00:00:00" for i in range(n)]


def value(f, rng, scenario: str, i: int = 0, base: float | None = None, signed: bool = False):
    if f.percent:
        v = rng.uniform(0.35, 0.98)
        return round(v, 4)
    scale = base if base is not None else 1200
    v = scale * rng.uniform(0.25, 1.0)
    if signed and rng.random() < 0.35:
        v = -v * 0.6
    if scenario == "stress":
        if i == 1:
            v *= 6.5
        elif i == 2:
            v = 0
        elif i == 4:
            return None
    decimals = 2 if "." in f.fmt else 0
    return round(v, decimals) if decimals else int(round(v))


def generic(c, scenario: str, rng: random.Random, signed: bool = False) -> list[dict]:
    """Every combination of the grouping fields, one row each, with random measures."""
    given = c.brief.get("sample") or {}
    dims, measures = [], []
    for f in c.all():
        if f.kind == "measure" or f.type == "quantitative" or f.numeric:
            measures.append(f)
        else:
            dims.append(f)
    axes = []
    for n, f in enumerate(dims):
        if f.type == "temporal":
            axes.append((f, months(scenario)))
        else:
            axes.append((f, categories(f, scenario, given, None if n == 0 else {"typical": 3, "stress": 6, "few": 2}[scenario])))
    limit = {"typical": 240, "stress": 1500, "few": 4}[scenario]
    total = 1
    for _, vals in axes:
        total *= max(1, len(vals))
    if total <= limit:
        rows = [{}]
        for f, vals in axes:
            rows = [{**r, f.key: v} for r in rows for v in vals]
    else:   # too many combinations: a sample of them, the first fields varying slowest
        rows = []
        for i in range(limit):
            row, step = {}, limit
            for f, vals in axes:
                step = max(1, step // len(vals))
                row[f.key] = vals[(i // step) % len(vals)]
            rows.append(row)
    for i, r in enumerate(rows):
        for f in measures:
            if f.type == "temporal":     # a measure with a point in time: the same for every row
                r[f.key] = ANCHOR.isoformat() + "T12:00:00"
            else:
                r[f.key] = value(f, rng, scenario, i, signed=signed)
    return rows


def rows(c, vtype, scenario: str = "typical") -> list[dict]:
    rng = random.Random(f"{c.brief['name']}|{scenario}")
    out = vtype.sample(c, scenario, rng)
    return generic(c, scenario, rng) if out is None else out
