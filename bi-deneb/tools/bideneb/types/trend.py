"""Development over time: lines."""
from .common import axis_q, Ctx, d, dim, enc, fk, legend, num, Option, register, Role, tooltip, VisualType, vl


@register
class Line(VisualType):
    id = "line"
    title = "Line over time"
    use = "How a value develops over many periods; up to about six series to compare their course."
    avoid = "Few periods that are read one by one (column); more than six series (multiples, or filter)."
    roles = [Role("x", ("temporal", "nominal"), help="the time axis: a date column, or ordered periods as text"),
             Role("value", ("quantitative",), help="height of the line"),
             Role("series", ("nominal",), required=False, help="one line per value of this column"),
             Role("reference", ("quantitative",), required=False, help="a second measure as dashed line (target, plan)")]
    options = [Option("points", False, "a marker at every value"),
               Option("zero", False, "the value axis starts at zero"),
               Option("labels", "last", "which values are written at the line", ("last", "none")),
               Option("interpolate", "linear", "shape of the line", ("linear", "monotone", "step-after"))]
    selection = False

    def build(self, c: Ctx) -> dict:
        b, x, val, ser, ref = c.brand, c.f("x"), c.f("value"), c.f("series"), c.f("reference")
        temporal = x.type == "temporal"
        xe = enc(x, axis={"title": None, "grid": False, "labelOverlap": True, "labelFlush": True, "ticks": True,
                          "tickSize": 4, "domain": True})
        if not temporal:
            xe["type"] = "ordinal"
            xe["sort"] = None
        ye = enc(val, axis=axis_q(val), scale={"zero": bool(c.opt("zero"))})
        if ser:
            color = enc(ser, scale={"range": b.palette("line")}, legend=legend(symbolType="stroke", symbolStrokeWidth=3))
        else:
            color = {"value": b.c("focus")}
        tip = tooltip(c, x, ser, val, ref)
        layers = [{"mark": {"type": "line", "interpolate": c.opt("interpolate", "linear")},
                   "encoding": {"color": color}}]
        if ref:
            layers.append({"mark": {"type": "line", "strokeDash": [5, 4], "strokeWidth": 1.5, "color": b.c("reference"),
                                    "interpolate": c.opt("interpolate", "linear")},
                           "encoding": {"y": {"field": fk(ref.key), "type": "quantitative"},
                                        **({"detail": {"field": fk(ser.key), "type": "nominal"}} if ser else {})}})
        show = bool(c.opt("points"))
        layers.append({"mark": {"type": "point", "filled": True, "size": 55 if show else 160, "tooltip": True},
                       "encoding": {"color": color, "tooltip": tip, "opacity": dim(c) if show else {"value": 0}}})
        transform = []
        if c.opt("labels", "last") == "last" and temporal:
            transform = [{"joinaggregate": [{"op": "max", "field": fk(x.key), "as": "bd_last"}],
                          **({"groupby": [fk(ser.key)]} if ser else {})}]
            last = f"time({d(x.key)}) == time(datum.bd_last)"
            layers.append({"mark": {"type": "point", "filled": True, "size": 60},
                           "encoding": {"color": color, "opacity": {"condition": {"test": last, "value": 1}, "value": 0}}})
            layers.append({"mark": {"type": "text", "align": "left", "baseline": "middle", "dx": 9,
                                    "fontWeight": 600, "color": b.c("text")},
                           "encoding": {"text": {"condition": {"test": last, "field": fk(val.key), "type": "quantitative",
                                                               **num(val)}, "value": ""}}})
        spec = vl(c, transform=transform, encoding={"x": xe, "y": ye}, layer=layers)
        if transform:   # room for the label after the last point
            spec["padding"] = {"left": 5, "top": 5, "bottom": 5, "right": 16 + 7 * max(5, len(val.fmt.split(";")[0]) + 1)}
        return spec

    def sample(self, c, scenario, rng):
        from .. import sample as sm
        x, val, ser, ref = c.f("x"), c.f("value"), c.f("series"), c.f("reference")
        xs = sm.months(scenario, {"typical": 24, "stress": 60, "few": 3}[scenario]) if x.type == "temporal" \
            else [f"KW {i + 1:02d}" for i in range({"typical": 12, "stress": 40, "few": 3}[scenario])]
        sers = sm.categories(ser, scenario, c.brief.get("sample") or {}, {"typical": 3, "stress": 8, "few": 2}[scenario]) \
            if ser else [None]
        rows = []
        for j, s in enumerate(sers):
            level = 0.9 if val.percent else 1000 / (j + 1)
            v = level
            for i, xv in enumerate(xs):
                v = max(level * 0.2, v + rng.uniform(-0.08, 0.09) * level)
                if val.percent:
                    v = min(0.999, v)
                row = {x.key: xv, val.key: round(v, 4 if val.percent else 1)}
                if scenario == "stress" and i == 7 and j == 0:
                    row[val.key] = None
                if ser:
                    row[ser.key] = s
                if ref:
                    row[ref.key] = round(level * (1 + i * 0.004), 4 if ref.percent else 1)
                rows.append(row)
        return rows
