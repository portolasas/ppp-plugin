"""Comparison with a reference: variance, bullet, dumbbell, waterfall."""
from .bars import cat_enc
from .common import axis_q, Ctx, d, dim, enc, fk, num, Option, register, Role, tooltip, VisualType, vl


def _delta(c: Ctx, val, ref) -> tuple[list, dict, str]:
    """Transforms for the difference to the reference, the text encoding and the test for 'good'."""
    mode = c.opt("delta", "percent")
    better = "datum.bd_delta >= 0" if c.opt("higherIsBetter", True) else "datum.bd_delta <= 0"
    v, r = f"{d(val.key)}", f"{d(ref.key)}"
    transform = [{"calculate": f"isValid({v}) && isValid({r}) ? {v} - {r} : null", "as": "bd_delta"},
                 {"calculate": f"isValid(datum.bd_delta) && {r} ? datum.bd_delta / abs({r}) : null", "as": "bd_rel"}]
    if mode == "percent":
        text = {"field": "bd_rel", "type": "quantitative", "format": "+0.0%;-0.0%", "formatType": "pbiFormat"}
    else:
        fmt = val.fmt.split(";")[0]
        text = {"field": "bd_delta", "type": "quantitative", "format": f"+{fmt};-{fmt}", "formatType": "pbiFormat"}
    return transform, text, better


class _Versus(VisualType):
    roles = [Role("category", ("nominal",), help="one row per category"),
             Role("value", ("quantitative",), help="the actual value"),
             Role("reference", ("quantitative",), help="what it is compared with: plan, target, previous year")]
    options = [Option("delta", "percent", "difference written next to each row", ("percent", "absolute", "none")),
               Option("higherIsBetter", True, "whether a value above the reference is good"),
               Option("sort", "value", "order of the rows", ("value", "category", "none"))]
    default_size = (560, 360)
    bullet = False

    def build(self, c: Ctx) -> dict:
        b, cat, val, ref = c.brand, c.f("category"), c.f("value"), c.f("reference")
        transform, dtext, better = _delta(c, val, ref)
        transform += [{"calculate": f"max({d(val.key)}, {d(ref.key)}, 0)", "as": "bd_end"},
                      {"joinaggregate": [{"op": "max", "field": "bd_end", "as": "bd_max"}]},
                      {"calculate": "datum.bd_max * 1.24", "as": "bd_room"}]
        s = c.opt("sort", "value")
        sort = {"field": fk(val.key), "op": "sum", "order": "descending"} if s == "value" else \
            "ascending" if s == "category" else None
        y = cat_enc(c, cat, "y", sort, "max(60, denebContainer.width * 0.3)")
        x = enc(val, axis=axis_q(val), scale={"zero": True, "nice": False})
        tip = tooltip(c, cat, val, ref) + [{"field": "bd_rel", "type": "quantitative", "title": "Abweichung",
                                            "format": "+0.0%;-0.0%", "formatType": "pbiFormat"}]
        if self.bullet:
            layers = [
                {"mark": {"type": "bar", "height": {"band": 0.8}, "color": b.c("band")},
                 "encoding": {"x": {"field": "bd_max", "type": "quantitative"}}},
                {"mark": {"type": "bar", "height": {"band": 0.4}, "color": b.c("focus"), "tooltip": True},
                 "encoding": {"opacity": dim(c), "tooltip": tip}},
                {"mark": {"type": "tick", "thickness": 3, "bandSize": {"expr": "bandwidth('y') * 0.8"},
                          "color": b.c("reference"), "tooltip": True},
                 "encoding": {"x": {"field": fk(ref.key), "type": "quantitative"}, "tooltip": tip}}]
        else:
            layers = [
                {"mark": {"type": "bar", "height": {"band": 0.78}, "color": b.c("context"), "tooltip": True},
                 "encoding": {"x": {"field": fk(ref.key), "type": "quantitative"}, "opacity": dim(c), "tooltip": tip}},
                {"mark": {"type": "bar", "height": {"band": 0.42}, "color": b.c("focus"), "tooltip": True},
                 "encoding": {"opacity": dim(c), "tooltip": tip}}]
        if c.opt("delta", "percent") != "none":
            layers.append({"mark": {"type": "point", "opacity": 0, "size": 1},
                           "encoding": {"x": {"field": "bd_room", "type": "quantitative"}}})
            layers.append({"mark": {"type": "text", "align": "left", "baseline": "middle", "dx": 8, "fontWeight": 600},
                           "encoding": {"x": {"field": "bd_end", "type": "quantitative"},
                                        "text": dtext,
                                        "color": {"condition": {"test": better, "value": b.c("goodText")},
                                                  "value": b.c("badText")},
                                        "opacity": dim(c)}})
        return vl(c, transform=transform, encoding={"y": y, "x": x}, layer=layers)

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        cat, val, ref = c.f("category"), c.f("value"), c.f("reference")
        rows = []
        for i, a in enumerate(sm.categories(cat, scenario, c.brief.get("sample") or {})):
            r = sm.value(ref, rng, "typical")
            v = r * rng.uniform(0.7, 1.25) if not val.percent else min(0.999, r * rng.uniform(0.85, 1.1))
            if scenario == "stress" and i == 1:
                v = r * 3
            rows.append({cat.key: a, val.key: round(v, 4 if val.percent else 0), ref.key: r})
        return rows


@register
class Variance(_Versus):
    id = "variance"
    title = "Actual against reference"
    use = "Actual against plan, target or previous year per category: reference as wide grey bar, actual as " \
          "narrow bar in front, the difference written next to it in good or bad colour."
    avoid = "No reference value; a development over time (line with reference)."


@register
class Bullet(_Versus):
    id = "bullet"
    title = "Bullet"
    use = "Degree of reaching a target per category: bar for the actual value, a marker for the target, on a " \
          "light band."
    avoid = "Targets that differ by orders of magnitude between rows (the common axis hides the small ones)."
    bullet = True


@register
class Dumbbell(VisualType):
    id = "dumbbell"
    title = "Dumbbell"
    use = "The change between two states per category (before and after, two years, two sites): two markers " \
          "joined by a line, so the gap is what the eye reads."
    avoid = "More than two states (line); values where the absolute level matters more than the gap (bar)."
    roles = [Role("category", ("nominal",), help="one row per category"),
             Role("from", ("quantitative",), help="the first state (drawn in the context colour)"),
             Role("to", ("quantitative",), help="the second state (drawn in the focus colour)")]
    options = [Option("sort", "to", "order of the rows", ("to", "gap", "category", "none")),
               Option("labels", True, "values next to both markers")]
    default_size = (560, 360)

    def build(self, c: Ctx) -> dict:
        b, cat, a, z = c.brand, c.f("category"), c.f("from"), c.f("to")
        transform = [{"calculate": f"{d(z.key)} - {d(a.key)}", "as": "bd_gap"},
                     {"calculate": f"min({d(a.key)}, {d(z.key)})", "as": "bd_lo"},
                     {"calculate": f"max({d(a.key)}, {d(z.key)})", "as": "bd_hi"}]
        s = c.opt("sort", "to")
        sort = {"field": fk(z.key), "op": "sum", "order": "descending"} if s == "to" else \
            {"field": "bd_gap", "op": "sum", "order": "descending"} if s == "gap" else \
            "ascending" if s == "category" else None
        y = cat_enc(c, cat, "y", sort, "max(60, denebContainer.width * 0.3)")
        y["axis"]["grid"] = True
        x = {"field": fk(a.key), "type": "quantitative", "scale": {"zero": False, "padding": 46},
             "axis": {"title": None, "grid": False, "tickCount": 5, "orient": "top", **num(z)}}
        tip = tooltip(c, cat, a, z)
        layers = [
            {"mark": {"type": "rule", "strokeWidth": 3, "color": b.c("grid")},
             "encoding": {"x": {"field": "bd_lo", "type": "quantitative"}, "x2": {"field": "bd_hi"}}},
            {"mark": {"type": "point", "filled": True, "size": 110, "color": b.c("context"), "opacity": 1, "tooltip": True},
             "encoding": {"tooltip": tip, "opacity": dim(c)}},
            {"mark": {"type": "point", "filled": True, "size": 110, "color": b.c("focus"), "opacity": 1, "tooltip": True},
             "encoding": {"x": {"field": fk(z.key), "type": "quantitative"}, "tooltip": tip, "opacity": dim(c)}}]
        if c.opt("labels", True):
            for key, f, color in ((a.key, a, b.c("textSecondary")), (z.key, z, b.c("text"))):
                left = f"{d(key)} <= datum.bd_lo && datum.bd_gap != 0" if key == a.key else \
                    f"{d(key)} < datum.bd_lo + 0 || ({d(key)} == datum.bd_lo && datum.bd_gap < 0)"
                layers.append({"mark": {"type": "text", "baseline": "middle", "color": color,
                                        "align": {"expr": f"{left} ? 'right' : 'left'"},
                                        "dx": {"expr": f"{left} ? -9 : 9"}},
                               "encoding": {"x": {"field": fk(key), "type": "quantitative"},
                                            "text": {"field": fk(key), "type": "quantitative", **num(f)},
                                            "opacity": dim(c)}})
        spec = vl(c, transform=transform, encoding={"y": y, "x": x}, layer=layers)
        spec["title"] = {**(spec.get("title") or {"text": ""}),
                         "subtitle": c.brief.get("subtitle") or f"{a.label} (grau) → {z.label} (dunkel)"}
        if not spec["title"]["text"]:
            spec["title"]["text"] = f"{a.label} → {z.label}"
        return spec

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        cat, a, z = c.f("category"), c.f("from"), c.f("to")
        rows = []
        for i, name in enumerate(sm.categories(cat, scenario, c.brief.get("sample") or {})):
            v = sm.value(a, rng, "typical")
            w = v * rng.uniform(0.75, 1.3) if not z.percent else min(0.999, v * rng.uniform(0.9, 1.1))
            if scenario == "stress" and i == 2:
                w = v
            rows.append({cat.key: name, a.key: v, z.key: round(w, 4 if z.percent else 0)})
        return rows


@register
class Waterfall(VisualType):
    id = "waterfall"
    title = "Waterfall"
    use = "How single contributions lead from a start to a result (bridge between plan and actual, between two " \
          "years, build-up of costs): each step starts where the last ended."
    avoid = "Steps without a meaningful order; many steps (more than about twelve)."
    roles = [Role("category", ("nominal",), help="one step per row, in the order of the order field"),
             Role("value", ("quantitative",), help="the change of this step, positive or negative"),
             Role("order", ("quantitative", "nominal", "temporal"), required=False,
                  help="column that puts the steps in order; without it the order of the rows")]
    options = [Option("total", "Gesamt", "label of the closing total bar; empty for none"),
               Option("higherIsBetter", True, "whether a positive step is good")]

    def build(self, c: Ctx) -> dict:
        b, cat, val, order = c.brand, c.f("category"), c.f("value"), c.f("order")
        good, bad = (b.c("good"), b.c("bad")) if c.opt("higherIsBetter", True) else (b.c("bad"), b.c("good"))
        sort = [{"field": fk(order.key)}] if order else []
        v = f"{d(val.key)}"
        transform = [
            {"window": [{"op": "sum", "field": fk(val.key), "as": "bd_end"}, {"op": "row_number", "as": "bd_n"}],
             **({"sort": sort} if sort else {}), "frame": [None, 0]},
            {"calculate": f"datum.bd_end - {v}", "as": "bd_start"},
            {"calculate": "max(datum.bd_start, datum.bd_end)", "as": "bd_top"},
            {"calculate": "min(datum.bd_start, datum.bd_end)", "as": "bd_bottom"},
            {"window": [{"op": "lead", "field": fk(cat.key), "as": "bd_next"}], "sort": [{"field": "bd_n"}]}]
        total = c.opt("total", "Gesamt")
        domain_sort = {"field": "bd_n", "op": "min"}
        x = enc(cat, sort=domain_sort, axis={"title": None, "labelOverlap": "parity", "labelLimit": 90})
        yaxis = axis_q(val)
        tip = tooltip(c, cat, val) + [{"field": "bd_end", "type": "quantitative", "title": "Stand", **num(val)}]
        fmt = val.fmt.split(";")[0]
        steps = [
            {"mark": {"type": "bar", "width": {"band": 0.7}, "tooltip": True},
             "encoding": {"y": {"field": "bd_start", "type": "quantitative", "axis": yaxis, "scale": {"zero": True}},
                          "y2": {"field": "bd_end"},
                          "color": {"condition": {"test": f"{v} >= 0", "value": good}, "value": bad},
                          "opacity": dim(c), "tooltip": tip}},
            {"mark": {"type": "rule", "color": b.c("reference"), "strokeWidth": 1, "xOffset": {"expr": "bandwidth('x') * 0.35"},
                      "x2Offset": {"expr": "-bandwidth('x') * 0.35"}},
             "transform": [{"filter": "isValid(datum.bd_next)"}],
             "encoding": {"x2": {"field": "bd_next"}, "y": {"field": "bd_end", "type": "quantitative"}}},
            {"mark": {"type": "text", "align": "center", "baseline": "bottom", "dy": -4, "color": b.c("text")},
             "encoding": {"y": {"field": "bd_top", "type": "quantitative"},
                          "text": {"condition": {"test": "bandwidth('x') >= 40", "field": fk(val.key), "type": "quantitative",
                                                 "format": f"+{fmt};-{fmt}", "formatType": "pbiFormat"}, "value": ""},
                          "opacity": dim(c)}}]
        layers = steps
        if total:
            agg = [{"aggregate": [{"op": "sum", "field": fk(val.key), "as": "bd_total"}, {"op": "max", "field": "bd_n", "as": "bd_n"}]},
                   {"calculate": repr(total), "as": cat.key}, {"calculate": "datum.bd_n + 1", "as": "bd_n"},
                   {"calculate": "max(datum.bd_total, 0)", "as": "bd_ttop"}]
            layers = steps + [
                {"transform": agg, "mark": {"type": "bar", "width": {"band": 0.7}, "color": b.c("focus")},
                 "encoding": {"y": {"field": "bd_total", "type": "quantitative"}}},
                {"transform": agg, "mark": {"type": "text", "align": "center", "baseline": "bottom", "dy": -4,
                                            "color": b.c("text"), "fontWeight": 600},
                 "encoding": {"y": {"field": "bd_ttop", "type": "quantitative"},
                              "text": {"field": "bd_total", "type": "quantitative", **num(val)}}}]
        return vl(c, transform=transform, encoding={"x": x}, layer=layers)

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        cat, val, order = c.f("category"), c.f("value"), c.f("order")
        names = sm.categories(cat, scenario, c.brief.get("sample") or {}, {"typical": 6, "stress": 14, "few": 2}[scenario])
        rows = []
        for i, n in enumerate(names):
            v = 1000 if i == 0 else int(rng.uniform(-260, 300))
            row = {cat.key: n, val.key: v}
            if order:
                row[order.key] = i + 1
            rows.append(row)
        return rows
