"""Bars and columns: ranking, comparison over few periods, stacked parts, Pareto."""
from .common import axis_q, Ctx, d, dim, enc, fk, legend, num, Option, register, Role, tooltip, VisualType, vl

PERIODS = {"day": ("yearmonthdate", "%d.%m."), "week": ("yearweek", "KW %V"), "month": ("yearmonth", "%b %y"),
           "quarter": ("yearquarter", "Q%q %y"), "year": ("year", "%Y")}
PERIOD = Option("period", "month", "length of one period when the category is a date", tuple(PERIODS))


def cat_enc(c: Ctx, cat, channel: str, sort=None, limit: str | None = None) -> dict:
    """The category on a band axis; a date becomes one band per period."""
    axis = {"title": None, "labelOverlap": "parity"} if channel == "x" else {"title": None}
    if limit:
        axis["labelLimit"] = {"expr": limit}
    if cat.type == "temporal":
        unit, fmt = PERIODS[c.opt("period", "month")]
        return {"field": fk(cat.key), "type": "ordinal", "timeUnit": unit, "axis": {**axis, "format": fmt}}
    out = enc(cat, axis=axis)
    out["sort"] = sort
    return out


def _sort(c: Ctx, value_key: str, default: str = "value"):
    s = c.opt("sort", default)
    if s == "value":
        return {"field": fk(value_key), "op": "sum", "order": "descending"}
    return "ascending" if s == "category" else None


def label_layers(c: Ctx, val, horizontal: bool, fill: str, threshold: float = 0.3, extra: str = "true") -> list:
    """Value labels: inside the end of the bar where the bar is long enough, next to it otherwise."""
    b = c.brand
    text = {"field": fk(val.key), "type": "quantitative", **num(val)}
    big = f"datum.bd_max > 0 && abs({d(val.key)}) >= {threshold} * datum.bd_max"
    neg = f"{d(val.key)} < 0"
    if horizontal:
        inside = {"type": "text", "baseline": "middle", "align": {"expr": f"{neg} ? 'left' : 'right'"},
                  "dx": {"expr": f"{neg} ? 6 : -6"}, "color": b.text_on(fill)}
        outside = {"type": "text", "baseline": "middle", "align": {"expr": f"{neg} ? 'right' : 'left'"},
                   "dx": {"expr": f"{neg} ? -6 : 6"}, "color": b.c("text")}
    else:
        inside = {"type": "text", "align": "center", "baseline": {"expr": f"{neg} ? 'bottom' : 'top'"},
                  "dy": {"expr": f"{neg} ? -5 : 5"}, "color": b.text_on(fill)}
        outside = {"type": "text", "align": "center", "baseline": {"expr": f"{neg} ? 'top' : 'bottom'"},
                   "dy": {"expr": f"{neg} ? 5 : -5"}, "color": b.c("text")}
    shown = lambda test: {"condition": {"test": f"({test}) && ({extra})", **text}, "value": ""}
    return [
        {"mark": inside, "encoding": {"text": shown(big), "opacity": dim(c)}},
        {"mark": outside, "encoding": {"text": shown(f"!({big}) && isValid({d(val.key)})"), "opacity": dim(c)}},
    ]


def max_abs(val) -> list:
    return [{"calculate": f"abs({d(val.key)})", "as": "bd_abs"},
            {"joinaggregate": [{"op": "max", "field": "bd_abs", "as": "bd_max"}]}]


@register
class Bar(VisualType):
    id = "bar"
    title = "Ranked bars"
    use = "Compare one value across categories, longest first; category names may be long."
    avoid = "More than about 25 categories (filter, or a top N measure); values over time (column or line)."
    roles = [Role("category", ("nominal",), help="one bar per value of this column"),
             Role("value", ("quantitative",), help="length of the bar")]
    options = [Option("sort", "value", "order of the bars", ("value", "category", "none")),
               Option("labels", True, "value at the end of each bar"),
               Option("emphasis", [], "category values drawn in the focus colour; all others in the context colour"),
               Option("axis", False, "value axis with grid lines in addition to the labels")]
    default_size = (520, 360)

    def build(self, c: Ctx) -> dict:
        b, cat, val = c.brand, c.f("category"), c.f("value")
        emphasis = c.opt("emphasis") or []
        fill = b.c("focus")
        color = {"value": fill}
        if emphasis:
            test = " || ".join(f"{d(cat.key)} == {v!r}" for v in emphasis)
            color = {"condition": {"test": test, "value": fill}, "value": b.c("context")}
        y = cat_enc(c, cat, "y", _sort(c, val.key), "max(60, denebContainer.width * 0.35)")
        x = enc(val, axis=axis_q(val) if c.opt("axis") else None, scale={"zero": True, "nice": bool(c.opt("axis"))})
        layers = [{"mark": {"type": "bar", "tooltip": True, "height": {"band": 0.72}},
                   "encoding": {"color": color, "opacity": dim(c), "tooltip": tooltip(c, cat, val)}}]
        if c.opt("labels", True):
            layers += label_layers(c, val, True, fill, 2 if emphasis else 0.3)
        return vl(c, transform=max_abs(val), encoding={"y": y, "x": x}, layer=layers)


@register
class Column(VisualType):
    id = "column"
    title = "Columns"
    use = "One value over a few periods or ordered categories (up to about 24), each period read on its own."
    avoid = "Many periods or a trend to follow (line); long category names (bar)."
    roles = [Role("category", ("temporal", "nominal"), help="one column per period or category"),
             Role("value", ("quantitative",), help="height of the column")]
    options = [PERIOD,
               Option("sort", "none", "order of the columns when the category is not a date", ("none", "value", "category")),
               Option("labels", True, "value above each column where the column is wide enough"),
               Option("emphasis", "none", "which column takes the focus colour; the others take the context colour",
                      ("none", "last")),
               Option("axis", True, "value axis with grid lines")]

    def build(self, c: Ctx) -> dict:
        b, cat, val = c.brand, c.f("category"), c.f("value")
        fill = b.c("focus")
        color = {"value": fill}
        transform = max_abs(val)
        if c.opt("emphasis", "none") == "last" and cat.type == "temporal":
            transform.append({"joinaggregate": [{"op": "max", "field": fk(cat.key), "as": "bd_last"}]})
            color = {"condition": {"test": f"time({d(cat.key)}) == time(datum.bd_last)", "value": fill},
                     "value": b.c("context")}
        x = cat_enc(c, cat, "x", _sort(c, val.key, "none"))
        y = enc(val, axis=axis_q(val) if c.opt("axis", True) else None, scale={"zero": True})
        layers = [{"mark": {"type": "bar", "tooltip": True, "width": {"band": 0.72}},
                   "encoding": {"color": color, "opacity": dim(c), "tooltip": tooltip(c, cat, val)}}]
        if c.opt("labels", True):
            layers += label_layers(c, val, False, fill, 2, "bandwidth('x') >= 38")
        return vl(c, transform=transform, encoding={"x": x, "y": y}, layer=layers)


@register
class Stacked(VisualType):
    id = "stacked"
    title = "Stacked bars"
    use = "A total per category and how a few parts (up to about six) make it up; with normalize: shares of 100 %."
    avoid = "Comparing the inner parts exactly (they do not share a baseline); more than about six parts."
    roles = [Role("category", ("nominal", "temporal"), help="one bar per category or period"),
             Role("series", ("nominal",), help="the parts of each bar"),
             Role("value", ("quantitative",), help="size of each part")]
    options = [Option("orientation", "auto", "bars or columns; auto takes columns for dates", ("auto", "horizontal", "vertical")),
               Option("normalize", False, "every bar fills 100 %, the parts show shares"),
               Option("labels", True, "value inside each part that is large enough"),
               Option("sort", "value", "order of the categories when they are not dates", ("value", "category", "none")),
               PERIOD]

    def build(self, c: Ctx) -> dict:
        b, cat, ser, val = c.brand, c.f("category"), c.f("series"), c.f("value")
        o = c.opt("orientation", "auto")
        horizontal = o == "horizontal" or (o == "auto" and cat.type != "temporal")
        norm = bool(c.opt("normalize"))
        cch, vch = ("y", "x") if horizontal else ("x", "y")
        pal = b.palette("category")
        stack = "normalize" if norm else "zero"
        value_axis = {"title": None, "grid": True, "tickCount": 5}
        value_axis.update({"format": "0%", "formatType": "pbiFormat"} if norm else num(val))
        transform = [{"joinaggregate": [{"op": "sum", "field": fk(val.key), "as": "bd_total"}], "groupby": [fk(cat.key)]},
                     {"joinaggregate": [{"op": "max", "field": "bd_total", "as": "bd_tmax"}]},
                     {"calculate": f"datum.bd_total ? {d(val.key)} / datum.bd_total : 0", "as": "bd_share"}]
        encoding = {cch: cat_enc(c, cat, cch, _sort(c, val.key), "max(60, denebContainer.width * 0.3)" if horizontal else None),
                    vch: {"field": fk(val.key), "type": "quantitative", "stack": stack, "axis": value_axis}}
        bar = {"type": "bar", "tooltip": True, ("height" if horizontal else "width"): {"band": 0.72}}
        share = {"field": "bd_share", "type": "quantitative", "title": "Anteil", "format": "0.0%", "formatType": "pbiFormat"}
        layers = [{"mark": bar, "encoding": {
            "color": enc(ser, scale={"range": pal}, legend=legend()),
            "order": {"field": fk(ser.key), "type": "nominal"}, "opacity": dim(c),
            "tooltip": tooltip(c, cat, ser, val) + [share]}}]
        if c.opt("labels", True):
            if norm:
                text, test = {"field": "bd_share", "type": "quantitative", "format": "0%", "formatType": "pbiFormat"}, \
                    "datum.bd_share >= 0.08"
            else:
                text, test = {"field": fk(val.key), "type": "quantitative", **num(val)}, \
                    f"datum.bd_tmax > 0 && {d(val.key)} >= {0.09 if horizontal else 0.07} * datum.bd_tmax"
            test += " && bandwidth('x') >= 38" if not horizontal else " && bandwidth('y') >= 16"
            layers.append({"mark": {"type": "text", "baseline": "middle", "align": "center"}, "encoding": {
                vch: {"field": fk(val.key), "type": "quantitative", "stack": stack, "bandPosition": 0.5},
                "order": {"field": fk(ser.key), "type": "nominal"},
                "text": {"condition": {"test": test, **text}, "value": ""},
                "color": enc(ser, scale={"range": [b.text_on(p) for p in pal]}, legend=None),
                "opacity": dim(c)}})
        return vl(c, transform=transform, encoding=encoding, layer=layers,
                  resolve={"scale": {"color": "independent"}})

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        given = c.brief.get("sample") or {}
        cat, ser, val = c.f("category"), c.f("series"), c.f("value")
        cats = sm.months(scenario) if cat.type == "temporal" else sm.categories(cat, scenario, given)
        sers = sm.categories(ser, scenario, given, {"typical": 4, "stress": 8, "few": 2}[scenario])
        return [{cat.key: a, ser.key: s, val.key: sm.value(val, rng, "typical", base=900 / (j + 1))}
                for a in cats for j, s in enumerate(sers)]


@register
class Pareto(VisualType):
    id = "pareto"
    title = "Pareto"
    use = "Which few categories cause most of a total (causes of downtime, defects, costs): bars in falling order " \
          "with the running share as a line."
    avoid = "Values that do not add up to a meaningful total; negative values."
    roles = [Role("category", ("nominal",), help="one bar per cause or category"),
             Role("value", ("quantitative",), help="height of the bar; all values add up to the total")]
    options = [Option("threshold", 0.8, "share marked by the reference line; 0 hides it")]

    def build(self, c: Ctx) -> dict:
        b, cat, val = c.brand, c.f("category"), c.f("value")
        line = b.palette("line")[1]
        pct = {"format": "0%", "formatType": "pbiFormat"}
        share_tip = {"field": "bd_share", "type": "quantitative", "title": "Kumulierter Anteil", "format": "0.0%",
                     "formatType": "pbiFormat"}
        transform = [
            {"window": [{"op": "sum", "field": fk(val.key), "as": "bd_cum"}],
             "sort": [{"field": fk(val.key), "order": "descending"}], "frame": [None, 0]},
            {"joinaggregate": [{"op": "sum", "field": fk(val.key), "as": "bd_sum"}]},
            {"calculate": "datum.bd_sum ? datum.bd_cum / datum.bd_sum : 0", "as": "bd_share"}]
        x = enc(cat, sort={"field": fk(val.key), "order": "descending"}, axis={"title": None, "labelOverlap": "parity",
                                                                          "labelLimit": 90})
        y2 = {"field": "bd_share", "type": "quantitative", "scale": {"domain": [0, 1]},
              "axis": {"title": None, "orient": "right", "grid": False, "tickCount": 5, **pct}}
        layers = [
            {"mark": {"type": "bar", "tooltip": True, "width": {"band": 0.72}, "color": b.c("focus")},
             "encoding": {"y": enc(val, axis=axis_q(val), scale={"zero": True}), "opacity": dim(c),
                          "tooltip": tooltip(c, cat, val) + [share_tip]}},
            {"layer": [
                {"mark": {"type": "line", "color": line, "strokeWidth": 2.5}, "encoding": {"y": y2}},
                {"mark": {"type": "point", "color": line, "filled": True, "size": 50, "opacity": 1, "tooltip": True},
                 "encoding": {"y": y2, "tooltip": tooltip(c, cat, val) + [share_tip]}}]},
        ]
        t = c.opt("threshold", 0.8)
        if t:
            layers[1]["layer"].append({"mark": {"type": "rule", "color": b.c("reference"), "strokeDash": [4, 4]},
                                       "encoding": {"x": None, "y": {"datum": t, "type": "quantitative", "axis": None}}})
        return vl(c, transform=transform, encoding={"x": x}, layer=layers, resolve={"scale": {"y": "independent"}})

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        cat, val = c.f("category"), c.f("value")
        cats = sm.categories(cat, scenario, c.brief.get("sample") or {}, {"typical": 8, "stress": 18, "few": 2}[scenario])
        return [{cat.key: a, val.key: int(1500 * (0.62 ** i) * rng.uniform(0.8, 1.2)) + 3} for i, a in enumerate(cats)]
