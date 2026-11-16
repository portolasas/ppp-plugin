"""Grids and lists: heatmap, traffic-light list."""
from .bars import PERIOD, cat_enc
from .common import Ctx, d, dim, enc, fk, num, Option, register, Role, tooltip, VisualType, vl

GREEN = ["grün", "gruen", "green", "ok", "im plan", "on track", "erledigt", "done", "g"]
YELLOW = ["gelb", "yellow", "amber", "beobachten", "watch", "warnung", "warning", "at risk", "y"]
RED = ["rot", "red", "eskalation", "escalation", "kritisch", "critical", "off track", "r"]


@register
class Heatmap(VisualType):
    id = "heatmap"
    title = "Heatmap"
    use = "One value for every combination of two dimensions (line by week, product by site): the pattern " \
          "shows where it is high or low; the numbers stay readable in the cells."
    avoid = "Exact comparison of single values (bar); sparse grids with many empty cells."
    roles = [Role("x", ("nominal", "temporal"), help="the columns of the grid"),
             Role("y", ("nominal",), help="the rows of the grid"),
             Role("value", ("quantitative",), help="colour and number of each cell")]
    options = [Option("labels", True, "number in each cell that is large enough"), PERIOD,
               Option("steps", 5, "number of colour steps (2 to 5)")]

    def build(self, c: Ctx) -> dict:
        b, x, y, val = c.brand, c.f("x"), c.f("y"), c.f("value")
        ramp = b.palette("sequential")
        n = max(2, min(int(c.opt("steps", 5)), len(ramp)))
        ramp = ramp[len(ramp) - n:] if n < len(ramp) else ramp
        on = [b.text_on(col) for col in ramp]
        v = f"{d(val.key)}"
        transform = [{"joinaggregate": [{"op": "min", "field": fk(val.key), "as": "bd_min"},
                                        {"op": "max", "field": fk(val.key), "as": "bd_max"}]},
                     {"calculate": f"datum.bd_max > datum.bd_min ? min({n - 1}, floor(({v} - datum.bd_min) / "
                                   f"(datum.bd_max - datum.bd_min) * {n})) : 0", "as": "bd_step"}]
        xe = cat_enc(c, x, "x", None)
        xe["axis"].update({"orient": "top", "labelLimit": 90})
        ye = cat_enc(c, y, "y", "ascending", "max(60, denebContainer.width * 0.28)")
        layers = [{"mark": {"type": "rect", "tooltip": True, "stroke": b.c("background"), "strokeWidth": 2},
                   "encoding": {"color": {"field": "bd_step", "type": "ordinal",
                                          "scale": {"domain": list(range(n)), "range": ramp},
                                          "legend": {"title": None, "orient": "bottom", "direction": "horizontal",
                                                     "symbolType": "square", "values": [0, n - 1],
                                                     "labelExpr": "datum.value == 0 ? 'niedrig' : 'hoch'"}},
                                "opacity": dim(c), "tooltip": tooltip(c, y, x, val)}}]
        if c.opt("labels", True):
            pick = "[" + ", ".join(repr(col) for col in on) + "][datum.bd_step]"
            layers.append({"mark": {"type": "text", "align": "center", "baseline": "middle", "color": {"expr": pick}},
                           "encoding": {"text": {"condition": {"test": "bandwidth('x') >= 40 && bandwidth('y') >= 18",
                                                               "field": fk(val.key), "type": "quantitative", **num(val)},
                                                 "value": ""}, "opacity": dim(c)}})
        return vl(c, transform=transform, encoding={"x": xe, "y": ye}, layer=layers)


@register
class Status(VisualType):
    id = "status"
    title = "Traffic-light list"
    use = "Status of work packages, lines, sites or measures as a list: a signal dot with its status in words, " \
          "the name, and a short remark or value."
    avoid = "Numbers to compare (bar, variance); more rows than fit the height (filter, or split by area)."
    roles = [Role("category", ("nominal",), help="what the row is about"),
             Role("status", ("nominal",), help="status as text; the option words maps it to green, yellow, red"),
             Role("detail", ("nominal",), required=False, help="short remark shown after the status"),
             Role("value", ("quantitative",), required=False, help="a number at the right end of the row")]
    options = [Option("green", GREEN, "status values (lower case) that count as green"),
               Option("yellow", YELLOW, "status values (lower case) that count as yellow"),
               Option("red", RED, "status values (lower case) that count as red"),
               Option("sort", "severity", "order of the rows", ("severity", "category", "none"))]
    default_size = (620, 320)

    def build(self, c: Ctx) -> dict:
        b, cat, st, det, val = c.brand, c.f("category"), c.f("status"), c.f("detail"), c.f("value")
        t = b.traffic()
        s = f"lower(trim(toString({d(st.key)})))"
        arr = lambda key, default: "[" + ", ".join(repr(str(x).lower()) for x in c.opt(key, default)) + "]"
        light = (f"indexof({arr('red', RED)}, {s}) >= 0 ? 'red' : indexof({arr('yellow', YELLOW)}, {s}) >= 0 ? 'yellow' : "
                 f"indexof({arr('green', GREEN)}, {s}) >= 0 ? 'green' : 'none'")
        transform = [{"calculate": light, "as": "bd_light"},
                     {"calculate": "indexof(['red', 'yellow', 'green', 'none'], datum.bd_light)", "as": "bd_rank"}]
        sort = c.opt("sort", "severity")
        ysort = {"field": "bd_rank", "op": "min"} if sort == "severity" else "ascending" if sort == "category" else None
        y = {"field": fk(cat.key), "type": "nominal", "axis": None, "sort": ysort,
             "scale": {"paddingInner": 0, "paddingOuter": 0}}
        col = lambda frac, px=0: {"value": {"expr": f"width * {frac} + {px}"}}
        text = lambda extra: {"type": "text", "align": "left", "baseline": "middle", **extra}
        tip = tooltip(c, cat, st, det, val)
        layers = [
            {"mark": {"type": "rule", "color": b.c("grid"), "yOffset": {"expr": "bandwidth('y') / 2"}},
             "encoding": {"x": {"value": 0}, "x2": {"value": {"expr": "width"}}}},
            {"mark": {"type": "point", "filled": True, "size": 150, "opacity": 1, "tooltip": True},
             "encoding": {"x": {"value": 10},
                          "color": {"field": "bd_light", "type": "nominal", "legend": None,
                                    "scale": {"domain": ["green", "yellow", "red", "none"],
                                              "range": [t["green"], t["yellow"], t["red"], t["none"]]}},
                          "tooltip": tip, "opacity": dim(c)}},
            {"mark": text({"fontWeight": 600, "color": b.c("text"), "limit": {"expr": "width * 0.36 - 34"}}),
             "encoding": {"x": {"value": 28}, "text": {"field": fk(cat.key), "type": "nominal"}, "opacity": dim(c)}},
            {"mark": text({"color": b.c("text"), "limit": {"expr": "width * 0.2 - 8"}}),
             "encoding": {"x": col(0.36), "text": {"field": fk(st.key), "type": "nominal"}, "opacity": dim(c)}}]
        if det:
            limit = "width * 0.44 - 8" if not val else "width * 0.32 - 8"
            layers.append({"mark": text({"color": b.c("textSecondary"), "limit": {"expr": limit}}),
                           "encoding": {"x": col(0.56), "text": {"field": fk(det.key), "type": "nominal"}, "opacity": dim(c)}})
        if val:
            layers.append({"mark": {"type": "text", "align": "right", "baseline": "middle", "color": b.c("text"),
                                    "fontWeight": 600},
                           "encoding": {"x": col(1, -4), "text": {"field": fk(val.key), "type": "quantitative", **num(val)},
                                        "opacity": dim(c)}})
        return vl(c, transform=transform, encoding={"y": y}, layer=layers)

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        cat, st, det, val = c.f("category"), c.f("status"), c.f("detail"), c.f("value")
        words = ["Im Plan", "Beobachten", "Eskalation", "Im Plan", "Offen"]
        notes = ["Lieferung bestätigt", "Material fehlt, Klärung bis Freitag", "", "Abnahme am 14.11.",
                 "Wartet auf Freigabe der Qualitätssicherung und auf den Lieferanten"]
        rows = []
        for i, name in enumerate(sm.categories(cat, scenario, c.brief.get("sample") or {},
                                               {"typical": 7, "stress": 16, "few": 2}[scenario])):
            row = {cat.key: name, st.key: words[i % len(words)]}
            if det:
                row[det.key] = notes[i % len(notes)]
            if val:
                row[val.key] = sm.value(val, rng, "typical")
            rows.append(row)
        return rows
