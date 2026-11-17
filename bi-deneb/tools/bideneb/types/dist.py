"""Relationship and distribution: scatter, histogram, box plot."""
from .bars import cat_enc
from .common import axis_q, Ctx, d, dim, enc, fk, legend, num, Option, register, Role, tooltip, VisualType, vl


def _kept(c: Ctx) -> str:
    key = c.f("id")
    text = c.brief.get("description") or c.brief.get("title") or c.brief["name"]
    return f"{text} (rows kept apart by '{key.key}')" if key else text


@register
class Scatter(VisualType):
    id = "scatter"
    title = "Scatter"
    use = "Whether two values move together, and which points fall out (throughput against scrap, cost " \
          "against duration): one point per row."
    avoid = "A value over time (line); fewer than about eight points (table or bar)."
    roles = [Role("x", ("quantitative",), help="horizontal position"),
             Role("y", ("quantitative",), help="vertical position"),
             Role("label", ("nominal",), help="what one point is (shown in the tooltip, optionally at the point)"),
             Role("color", ("nominal",), required=False, help="group of the point, up to six")]
    options = [Option("labels", False, "name next to every point (only for few points)"),
               Option("zero", False, "both axes start at zero")]

    def build(self, c: Ctx) -> dict:
        b, x, y, lab, col = c.brand, c.f("x"), c.f("y"), c.f("label"), c.f("color")
        zero = bool(c.opt("zero"))
        xe = enc(x, axis={**axis_q(x), "title": x.label, "grid": True}, scale={"zero": zero, "padding": 16})
        ye = enc(y, axis={**axis_q(y), "title": y.label}, scale={"zero": zero, "padding": 16})
        color = enc(col, scale={"range": b.palette("line")}, legend=legend(symbolType="circle")) if col \
            else {"value": b.c("focus")}
        layers = [{"mark": {"type": "point", "filled": True, "size": 80, "tooltip": True},
                   "encoding": {"color": color, "opacity": dim(c, 0.85), "tooltip": tooltip(c, lab, col, x, y)}}]
        if c.opt("labels"):
            layers.append({"mark": {"type": "text", "align": "left", "baseline": "middle", "dx": 8,
                                    "color": b.c("text"), "limit": 120},
                           "encoding": {"text": {"field": fk(lab.key), "type": "nominal"}, "opacity": dim(c)}})
        return vl(c, encoding={"x": xe, "y": ye}, layer=layers)

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        x, y, lab, col = c.f("x"), c.f("y"), c.f("label"), c.f("color")
        n = {"typical": 40, "stress": 400, "few": 2}[scenario]
        groups = sm.categories(col, scenario, c.brief.get("sample") or {}, {"typical": 3, "stress": 6, "few": 2}[scenario]) \
            if col else [None]
        rows = []
        for i in range(n):
            a = rng.uniform(0.1, 1)
            bb = min(1.0, max(0.02, a * 0.7 + rng.gauss(0, 0.12)))
            row = {lab.key: f"{lab.label} {i + 1}",
                   x.key: round(a, 4) if x.percent else round(a * 1200, 1),
                   y.key: round(bb, 4) if y.percent else round(bb * 800, 1)}
            if col:
                row[col.key] = groups[i % len(groups)]
            rows.append(row)
        return rows


@register
class Histogram(VisualType):
    id = "histogram"
    title = "Histogram"
    use = "How the single values of one numeric column are spread (cycle times, weights, durations): how many " \
          "rows fall into each range."
    avoid = "A measure that is already aggregated (bar or column); few rows (below about 30)."
    roles = [Role("value", ("quantitative",), help="a numeric column with one value per row, not a measure",
                  only="column"),
             Role("id", ("nominal",), required=False,
                  help="a key column that keeps the rows apart, when equal values would otherwise be merged")]
    options = [Option("bins", 20, "largest number of ranges")]
    selection = False

    def build(self, c: Ctx) -> dict:
        b, val = c.brand, c.f("value")
        x = {"field": fk(val.key), "type": "quantitative", "bin": {"maxbins": int(c.opt("bins", 20))},
             "axis": {"title": val.label, **num(val), "labelOverlap": True, "grid": False}}
        y = {"aggregate": "count", "type": "quantitative",
             "axis": {"title": "Anzahl", "grid": True, "tickCount": 5, "tickMinStep": 1, "format": "#,0",
                      "formatType": "pbiFormat"}}
        return vl(c, description=_kept(c), mark={"type": "bar", "color": b.c("focus"), "tooltip": True, "binSpacing": 2},
                  encoding={"x": x, "y": y,
                            "tooltip": [{"field": fk(val.key), "type": "quantitative", "bin": {"maxbins": int(c.opt("bins", 20))},
                                         "title": val.label},
                                        {"aggregate": "count", "type": "quantitative", "title": "Anzahl"}]})

    def sample(self, c, scenario, rng):
        val, key = c.f("value"), c.f("id")
        n = {"typical": 300, "stress": 3000, "few": 3}[scenario]
        rows = []
        for i in range(n):
            v = max(0.0, rng.gauss(42, 9) + (rng.random() < 0.05) * 40)
            row = {val.key: round(v, 1)}
            if key:
                row[key.key] = f"{key.label} {i + 1}"
            rows.append(row)
        return rows


@register
class Boxplot(VisualType):
    id = "boxplot"
    title = "Box plot"
    use = "Compare the spread of a numeric column between groups (durations per line, weights per product): " \
          "median, middle half and range per group."
    avoid = "An audience that does not read box plots (use bar with the median as measure); few rows per group."
    roles = [Role("category", ("nominal",), help="one box per group"),
             Role("value", ("quantitative",), help="a numeric column with one value per row, not a measure",
                  only="column"),
             Role("id", ("nominal",), required=False,
                  help="a key column that keeps the rows apart, when equal values would otherwise be merged")]
    options = [Option("extent", "1.5", "whiskers: 1.5 times the middle half with outliers as points, or the full range",
                      ("1.5", "min-max"))]
    selection = False
    default_size = (560, 360)

    def build(self, c: Ctx) -> dict:
        b, cat, val = c.brand, c.f("category"), c.f("value")
        ext = c.opt("extent", "1.5")
        mark = {"type": "boxplot", "extent": "min-max" if ext == "min-max" else 1.5, "size": 18,
                "color": b.c("focus"),
                "box": {"color": b.c("focus")}, "median": {"fill": b.hex("white"), "stroke": b.c("focus"), "strokeWidth": 1},
                "rule": {"color": b.c("textSecondary")}, "ticks": {"color": b.c("textSecondary")},
                "outliers": {"color": b.c("textSecondary"), "size": 18, "filled": True}}
        y = cat_enc(c, cat, "y", "ascending", "max(60, denebContainer.width * 0.3)")
        x = enc(val, axis={**axis_q(val), "title": val.label}, scale={"zero": False})
        return vl(c, description=_kept(c), mark=mark, encoding={"y": y, "x": x})

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        cat, val, key = c.f("category"), c.f("value"), c.f("id")
        rows = []
        for j, g in enumerate(sm.categories(cat, scenario, c.brief.get("sample") or {},
                                            {"typical": 5, "stress": 12, "few": 2}[scenario])):
            for i in range({"typical": 60, "stress": 200, "few": 4}[scenario]):
                row = {cat.key: g, val.key: round(max(1, rng.gauss(40 + j * 4, 6 + j) + (rng.random() < 0.03) * 35), 1)}
                if key:
                    row[key.key] = f"{key.label} {j}-{i}"
                rows.append(row)
        return rows
