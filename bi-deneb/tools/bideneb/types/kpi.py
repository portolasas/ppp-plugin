"""KPI card: one number, its distance to a reference and its recent course. Written in Vega for exact layout."""
from .common import Ctx, d, fk, Option, q, register, Role, VEGA_SCHEMA, VisualType


@register
class Kpi(VisualType):
    id = "kpi"
    title = "KPI card"
    use = "One key figure at a glance: the current value large, the difference to plan or previous period in " \
          "good or bad colour, and the course of the last periods as a small line."
    avoid = "Several figures to compare (bar, variance); a course that needs an axis to be read (line)."
    provider = "vega"
    roles = [Role("value", ("quantitative",), help="the key figure"),
             Role("reference", ("quantitative",), required=False, help="plan, target or previous period"),
             Role("date", ("temporal",), required=False,
                  help="a date column: the card shows the latest period and the course before it; without it "
                       "the dataset must hold one row")]
    options = [Option("delta", "percent", "how the difference is written", ("percent", "absolute")),
               Option("higherIsBetter", True, "whether a value above the reference is good"),
               Option("referenceLabel", "ggü. Plan", "words after the difference"),
               Option("sparkline", True, "small line with the course when a date is given")]
    selection = False
    min_size = (180, 96)
    default_size = (320, 160)

    def build(self, c: Ctx) -> dict:
        b, val, ref, date = c.brand, c.f("value"), c.f("reference"), c.f("date")
        v, r = f"datum[{q(val.key)}]", f"datum[{q(ref.key)}]" if ref else "null"
        d = f"datum[{q(date.key)}]" if date else None
        spark = bool(date and c.opt("sparkline", True))
        fmt = val.fmt.split(";")[0]
        good = "datum.delta >= 0" if c.opt("higherIsBetter", True) else "datum.delta <= 0"
        if c.opt("delta", "percent") == "percent":
            delta_text = "pbiFormat(datum.rel, '+0.0%;-0.0%')"
            has_delta = "isValid(datum.rel)"
        else:
            delta_text = f"pbiFormat(datum.delta, {q('+' + fmt + ';-' + fmt)})"
            has_delta = "isValid(datum.delta)"
        last = [{"type": "filter", "expr": f"isValid({v})"}]
        if date:
            last += [{"type": "collect", "sort": {"field": fk(date.key), "order": "descending"}}]
        last += [{"type": "window", "ops": ["row_number"], "as": ["n"]}, {"type": "filter", "expr": "datum.n == 1"},
                 {"type": "formula", "as": "v", "expr": v},
                 {"type": "formula", "as": "delta", "expr": f"isValid({r}) ? {v} - {r} : null" if ref else "null"},
                 {"type": "formula", "as": "rel", "expr": f"isValid(datum.delta) && {r} ? datum.delta / abs({r}) : null"
                  if ref else "null"},
                 {"type": "formula", "as": "good", "expr": good}]
        data = [{"name": "dataset"}, {"name": "last", "source": "dataset", "transform": last}]
        signals = [
            {"name": "W", "update": "max(120, width)"},
            {"name": "H", "update": "max(64, height)"},
            {"name": "pad", "value": 12},
            {"name": "big", "update": f"H >= 150 && W >= 240 ? {b.size('kpi')} : H >= 104 ? 22 : 18"},
            {"name": "titleH", "value": 20 if c.brief.get("title") else 0},
            {"name": "textBottom", "update": "pad + titleH + big + 30"},
            {"name": "side", "update": "W >= 380"},
            {"name": "sparkOn", "update": "side || H - textBottom >= 40" if spark else "false"},
            {"name": "sx0", "update": "side ? W * 0.52 : pad"},
            {"name": "sx1", "update": "W - pad - 6"},
            {"name": "sy0", "update": "side ? pad + 10 : textBottom + 6"},
            {"name": "sy1", "update": "H - pad - 4"}]
        marks = []
        if c.brief.get("title"):
            marks.append({"type": "text", "encode": {"update": {
                "x": {"signal": "pad"}, "y": {"signal": "pad"}, "baseline": {"value": "top"},
                "text": {"value": c.brief["title"]}, "fill": {"value": b.c("textSecondary")},
                "fontSize": {"value": b.size("title")}, "fontWeight": {"value": 600},
                "limit": {"signal": "(side && sparkOn ? sx0 : W) - 2 * pad"}}}})
        marks.append({"type": "text", "name": "value", "from": {"data": "last"}, "encode": {"update": {
            "x": {"signal": "pad"}, "y": {"signal": "pad + titleH + 2"}, "baseline": {"value": "top"},
            "text": {"signal": f"pbiFormat(datum.v, {q(val.fmt)})"}, "fill": {"value": b.c("text")},
            "fontSize": {"signal": "big"}, "fontWeight": {"value": 700},
            "tooltip": {"signal": "{" + f"{q(val.label)}: pbiFormat(datum.v, {q(val.fmt)})"
                                  + (f", {q(ref.label)}: pbiFormat({r}, {q(ref.fmt)})" if ref else "") + "}"}}}})
        if ref:
            marks.append({"type": "text", "name": "delta", "from": {"data": "last"}, "encode": {"update": {
                "x": {"signal": "pad"}, "y": {"signal": "pad + titleH + big + 12"}, "baseline": {"value": "top"},
                "text": {"signal": f"{has_delta} ? (datum.delta >= 0 ? '▲ ' : '▼ ') + {delta_text} + ' ' + "
                                   f"{q(c.opt('referenceLabel', 'ggü. Plan'))} : ''"},
                "fill": {"signal": f"datum.good ? {q(b.c('goodText'))} : {q(b.c('badText'))}"},
                "fontSize": {"value": b.size("label")}, "fontWeight": {"value": 600},
                "limit": {"signal": "(side && sparkOn ? sx0 : W) - 2 * pad"}}}})
        scales = []
        if spark:
            data.append({"name": "course", "source": "dataset", "transform": [
                {"type": "filter", "expr": f"isValid({v}) && isValid({d})"},
                {"type": "collect", "sort": {"field": fk(date.key)}}]})
            scales = [{"name": "sx", "type": "time", "domain": {"data": "course", "field": fk(date.key)},
                       "range": [{"signal": "sx0"}, {"signal": "sx1"}]},
                      {"name": "sy", "type": "linear", "zero": False, "domain": {"data": "course", "field": fk(val.key)},
                       "range": [{"signal": "sy1"}, {"signal": "sy0"}]}]
            on = {"signal": "sparkOn ? 1 : 0"}
            marks += [
                {"type": "line", "from": {"data": "course"}, "encode": {"update": {
                    "x": {"scale": "sx", "field": fk(date.key)}, "y": {"scale": "sy", "field": fk(val.key)},
                    "stroke": {"value": b.c("focus")}, "strokeWidth": {"value": 2}, "opacity": on}}},
                {"type": "symbol", "from": {"data": "last"}, "encode": {"update": {
                    "x": {"scale": "sx", "field": fk(date.key)}, "y": {"scale": "sy", "field": fk(val.key)},
                    "fill": {"value": b.c("focus")}, "size": {"value": 60}, "opacity": on}}},
                {"type": "symbol", "from": {"data": "course"}, "encode": {"update": {
                    "x": {"scale": "sx", "field": fk(date.key)}, "y": {"scale": "sy", "field": fk(val.key)},
                    "fill": {"value": b.c("focus")}, "size": {"value": 140}, "opacity": {"value": 0},
                    "tooltip": {"signal": "{" + f"{q(date.label)}: pbiFormat({d}, {q(date.fmt)}), "
                                          f"{q(val.label)}: pbiFormat({v}, {q(val.fmt)})" + "}"}}}}]
        return {"$schema": VEGA_SCHEMA, "description": c.brief.get("description") or c.brief.get("title") or c.brief["name"],
                "padding": 0, "autosize": "none",
                "signals": signals, "data": data, "scales": scales, "marks": marks}

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        val, ref, date = c.f("value"), c.f("reference"), c.f("date")
        xs = sm.months(scenario, {"typical": 13, "stress": 48, "few": 1}[scenario]) if date else [None]
        level = 0.86 if val.percent else (1234567.0 if scenario == "stress" else 4200.0)
        rows, v = [], level
        for x in xs:
            v = v * (1 + rng.uniform(-0.06, 0.07))
            if val.percent:
                v = min(0.999, v)
            row = {val.key: round(v, 4 if val.percent else 1)}
            if date:
                row[date.key] = x
            if ref:
                row[ref.key] = round(level * 1.02, 4 if ref.percent else 1)
            rows.append(row)
        return rows
