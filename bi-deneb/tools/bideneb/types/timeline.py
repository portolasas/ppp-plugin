"""Things with a start and an end on a time axis; parts of a whole."""
import datetime as dt

from .bars import cat_enc
from .common import Ctx, d, dim, enc, fk, legend, num, Option, register, Role, tooltip, VisualType, vl


@register
class Timeline(VisualType):
    id = "timeline"
    title = "Timeline (Gantt)"
    use = "Orders, batches, phases or downtimes with start and end on a time axis, one row per resource or " \
          "task; several segments may follow each other in one row."
    avoid = "Durations to compare without their position in time (bar); shift bands, zoom or collapsing groups " \
            "(a custom Vega specification on a segment table)."
    roles = [Role("row", ("nominal",), help="one row per resource, line or task"),
             Role("start", ("temporal",), help="start of the segment"),
             Role("end", ("temporal",), help="end of the segment"),
             Role("color", ("nominal",), required=False, help="kind of the segment (phase, status), up to ten"),
             Role("label", ("nominal",), required=False, help="text inside the segment where it fits"),
             Role("now", ("temporal",), required=False, help="a measure with the current time or the data state")]
    options = [Option("sort", "start", "order of the rows", ("start", "row", "none"))]
    default_size = (760, 360)

    def build(self, c: Ctx) -> dict:
        b = c.brand
        row, start, end, col, lab, now = (c.f(r) for r in ("row", "start", "end", "color", "label", "now"))
        pal = b.palette("category")
        s = c.opt("sort", "start")
        ysort = {"field": fk(start.key), "op": "min"} if s == "start" else "ascending" if s == "row" else None
        y = cat_enc(c, row, "y", ysort, "max(60, denebContainer.width * 0.22)")
        y["axis"]["grid"] = False
        y["scale"] = {"paddingInner": 0.3, "paddingOuter": 0.2}
        x = {"field": fk(start.key), "type": "temporal",
             "axis": {"title": None, "orient": "top", "grid": True, "labelOverlap": True, "labelFlush": True,
                      "tickCount": {"expr": "max(2, floor(width / 90))"}}}
        tip = tooltip(c, row, col, lab, start, end)
        fill = enc(col, scale={"range": pal}, legend=legend()) if col else {"value": b.c("focus")}
        layers = [{"mark": {"type": "bar", "tooltip": True},
                   "encoding": {"x2": {"field": fk(end.key)}, "color": fill, "opacity": dim(c), "tooltip": tip}}]
        if lab:
            fits = (f"scale('x', {d(end.key)}) - scale('x', {d(start.key)}) > "
                    f"14 + 6.6 * length('' + {d(lab.key)}) && isValid({d(lab.key)}) && bandwidth('y') >= 15")
            tcolor = enc(col, scale={"range": [b.text_on(p) for p in pal]}, legend=None) if col \
                else {"value": b.text_on(b.c("focus"))}
            layers.append({"mark": {"type": "text", "align": "left", "baseline": "middle", "dx": 5},
                           "encoding": {"text": {"condition": {"test": fits, "field": fk(lab.key), "type": "nominal"},
                                                 "value": ""}, "color": tcolor, "opacity": dim(c)}})
        if now:
            layers.append({"transform": [{"aggregate": [{"op": "max", "field": fk(now.key), "as": "bd_now"}]}],
                           "mark": {"type": "rule", "color": b.c("text"), "strokeWidth": 2, "strokeDash": [5, 3]},
                           "encoding": {"x": {"field": "bd_now", "type": "temporal"}, "y": None}})
        spec = vl(c, encoding={"y": y, "x": x}, layer=layers)
        if col and lab:
            spec["resolve"] = {"scale": {"color": "independent"}}
        return spec

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        row, start, end, col, lab, now = (c.f(r) for r in ("row", "start", "end", "color", "label", "now"))
        given = c.brief.get("sample") or {}
        rows_ = sm.categories(row, scenario, given, {"typical": 6, "stress": 16, "few": 2}[scenario])
        kinds = sm.categories(col, "typical", given, 4) if col else [None]
        t0 = dt.datetime(2026, 11, 2, 6, 0)
        out = []
        for r in rows_:
            t = t0 + dt.timedelta(hours=rng.randint(0, 10))
            for i in range({"typical": 5, "stress": 14, "few": 1}[scenario]):
                d = dt.timedelta(hours=rng.choice([1, 2, 4, 7, 12]))
                item = {row.key: r, start.key: t.isoformat(timespec="seconds"),
                        end.key: (t + d).isoformat(timespec="seconds")}
                if col:
                    item[col.key] = kinds[i % len(kinds)]
                if lab:
                    item[lab.key] = None if scenario == "stress" and i == 3 else f"{1121300 + len(out)}"
                if now:
                    item[now.key] = (t0 + dt.timedelta(days=2, hours=3)).isoformat(timespec="seconds")
                out.append(item)
                t += d + dt.timedelta(hours=rng.choice([0, 0, 1, 3]))
        return out


@register
class Donut(VisualType):
    id = "donut"
    title = "Donut"
    use = "Shares of one total with up to five parts, when the total itself is the headline (it stands in the " \
          "middle)."
    avoid = "More than five parts, parts of similar size, or several totals to compare (stacked with normalize, or bar)."
    roles = [Role("category", ("nominal",), help="the parts"),
             Role("value", ("quantitative",), help="size of each part")]
    options = [Option("labels", True, "share in each part that is large enough"),
               Option("total", "Gesamt", "word under the total in the middle; empty for no total")]
    default_size = (420, 360)

    def build(self, c: Ctx) -> dict:
        b, cat, val = c.brand, c.f("category"), c.f("value")
        pal = b.palette("category")
        outer, inner = "min(width, height) / 2 - 2", "min(width, height) * 0.3"
        transform = [{"joinaggregate": [{"op": "sum", "field": fk(val.key), "as": "bd_sum"}]},
                     {"calculate": f"datum.bd_sum ? {d(val.key)} / datum.bd_sum : 0", "as": "bd_share"}]
        share = {"field": "bd_share", "type": "quantitative", "title": "Anteil", "format": "0.0%", "formatType": "pbiFormat"}
        theta = {"field": fk(val.key), "type": "quantitative", "stack": True}
        order = {"field": fk(val.key), "type": "quantitative", "sort": "descending"}
        layers = [{"mark": {"type": "arc", "outerRadius": {"expr": outer}, "innerRadius": {"expr": inner},
                            "stroke": b.c("background"), "strokeWidth": 2, "tooltip": True},
                   "encoding": {"color": enc(cat, scale={"range": pal}, legend=legend()),
                                "opacity": dim(c), "tooltip": tooltip(c, cat, val) + [share]}}]
        if c.opt("labels", True):
            layers.append({"mark": {"type": "text", "radius": {"expr": f"({outer} + {inner}) / 2"}, "fontWeight": 600},
                           "encoding": {"text": {"condition": {"test": "datum.bd_share >= 0.07", "field": "bd_share",
                                                               "type": "quantitative", "format": "0%",
                                                               "formatType": "pbiFormat"}, "value": ""},
                                        "color": enc(cat, scale={"range": [b.text_on(p) for p in pal]}, legend=None),
                                        "opacity": dim(c)}})
        if c.opt("total", "Gesamt"):
            agg = [{"aggregate": [{"op": "sum", "field": fk(val.key), "as": "bd_total"}]}]
            layers.append({"transform": agg, "mark": {"type": "text", "fontSize": b.size("kpiSmall"), "fontWeight": 600,
                                                      "color": b.c("text"), "dy": -4},
                           "encoding": {"theta": None, "order": None,
                                        "text": {"field": "bd_total", "type": "quantitative", **num(val)}}})
            layers.append({"transform": agg, "mark": {"type": "text", "color": b.c("textSecondary"), "dy": 16},
                           "encoding": {"theta": None, "order": None, "text": {"value": c.opt("total", "Gesamt")}}})
        return vl(c, transform=transform, encoding={"theta": theta, "order": order}, layer=layers,
                  resolve={"scale": {"color": "independent"}}, view={"stroke": None})

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        cat, val = c.f("category"), c.f("value")
        names = sm.categories(cat, scenario, c.brief.get("sample") or {}, {"typical": 4, "stress": 9, "few": 2}[scenario])
        return [{cat.key: n, val.key: int(1000 * (0.6 ** i) * rng.uniform(0.8, 1.2)) + 5} for i, n in enumerate(names)]
