# Writing a specification by hand (type custom)

Status per statement: **[S]** read in the Deneb source (2.0.1), **[B]** observed in Power BI Desktop, **[L]** shown by
the local render, **[O]** open. Deneb 2.0.1 runs Vega 6.4.0 and Vega-Lite 6.4.3.

## Loop
`bideneb check <name>` after every change: it renders typical and stress rows in the sizes of the brief and prints
findings. Build one mark at a time and look at the contact sheet before adding the next. Rows that the generic
generator cannot guess (status words, start before end, a certain key) go into `<name>.data.json` as
`{"typical": [...], "stress": [...]}`: invented rows with the dataset keys, dates as `2026-11-02T06:00:00`.

## Vega-Lite or Vega
Vega-Lite for one chart with axes and layers. Vega when the layout is yours: several header rows, bands in the
background, scrolling, buttons, signals for interaction, the advanced cross-filter.

## What Deneb gives the specification
- **Rows:** data source `dataset`. Vega-Lite: `"data": {"name": "dataset"}`; Vega: an entry `{"name": "dataset"}` in
  `data`. Nothing else loads: no `url` except `data:` URIs, images included. [S]
- **Field keys:** the display name of the field; `\ " . [ ]` each become `_` (`Sparte.Name` → `Sparte_Name`). In
  expressions write `datum['Plan Umsatz']`. The brief knows the keys; finding F1 names a wrong one. [S]
- **Every row** carries `__row__` (0-based) and, with cross-filter on, `__selected__` = `on`, `off` or `neutral`. [S]
- **Dates** arrive as JavaScript dates in local time. Use the local functions (`hours`, `timeFormat`, `datetime(y, m,
  d, h, mi)`); `utc…` shifts every value by the time-zone offset (finding D6). Convert defensively with
  `time(toDate(datum.Start))`. [S] Whether a value keeps the wall time of the model or is shifted is not confirmed
  in Desktop: keep the conversion to local time in the model and let the user compare one known value. [O]
- **Size:** the signal `denebContainer` with `width`, `height` (and scroll values). Vega-Lite: leave `width` and
  `height` out, Deneb sets `"container"`; for an expression use `denebContainer.width` or the signals `width`,
  `height`. Vega: leave top-level `width` and `height` out, Deneb sets them to the container; set `"autosize":
  "none"` and `"padding": 0` and lay out from the signals `width` and `height`. A fixed size does not follow the
  visual (finding D5); a canvas larger than the container gets scroll bars (finding P3). [S][L]
- **Measures** arrive on every row. A value that is one number for the whole visual (a window start, "now") is
  written as `CALCULATE(…, ALLSELECTED())` in DAX and reduced with an `aggregate` in the specification. [B]

## Formatting
- Numbers and dates: `"format": "#,0.0", "formatType": "pbiFormat"` in Vega-Lite, `pbiFormat(value, '#,0.0')` in an
  expression: the Power BI format string of the measure, in the locale of the report. d3 formats ignore both
  (finding D10). Sections work: `'+0.0%;-0.0%'`. `pbiFormatAutoUnit` shortens to thousands and millions. [S]
- The config of a brand (written by `bideneb new`) carries font, sizes, colours and the German d3 locale for axes.
  Keep free values out of the specification; a deviation belongs into `<name>.config.json`.

## Colour
- Write the hex values of the brand tokens (`bideneb brand`): fill of data `focus`, the rest of a comparison
  `context`, good and bad `good`/`bad` with their text colours, series `category`, lines and small markers `line`.
- Text on a fill: the brand's text colour for that fill; the render checks the contrast (finding P7). Accent
  Green is a fill, never text or a thin line on white.
- `pbiColor(…)` and the schemes `pbiColorNominal`, `pbiColorOrdinal`, `pbiColorLinear`, `pbiColorDivergent` follow the
  report theme: brand colours only while the brand theme is applied (finding D11). [S]
- Hatching: `"fill": "url(#diagonal-stripe-1)"`; ids `diagonal-stripe-1…6`, `horizontal-stripe-1…9`,
  `vertical-stripe-1…9`, `dots-1…9`, `circles-1…9`, `crosshatch`, `houndstooth`. SVG renderer only. [S][L]

## Tooltip
Vega-Lite: `"tooltip": true` on the mark, or a `tooltip` encoding with the fields and `formatType: "pbiFormat"`.
Vega: `"tooltip": {"signal": "{'Charge': datum.Charge, 'Dauer': pbiFormat(datum.Dauer_h, '0.0')}"}` in `encode`. A
tooltip key that equals a dataset key gets the format of the model. [S]

## Cross-filter (a click filters the other visuals)
- **Simple** (Vega-Lite and Vega): set `"crossFilter": true` in the brief; Deneb handles the click. A mark drawn
  from a dataset row (filter, calculate, window, joinaggregate and stack keep rows) selects that row. A mark from
  aggregated rows has no `__row__`: Deneb then selects every row that has the values of the dataset fields the mark
  still carries, so keep the grouping fields under their names; `__selected__` is not on aggregated rows (finding
  X3). Show the state yourself: opacity 0.3 where `__selected__ == 'off'` (finding X1). At most 50 selected rows
  by default, 250 at most in this mode (`"maxDataPoints"` under `interaction`). [S]
- **Advanced** (Vega): a signal calls `pbiCrossFilterApply(event, "datum['Kampagne'] == _{Kampagne}_")` on a click
  of the mark and `pbiCrossFilterClear()` on a click of the empty area. `_{Field}_` takes the value of the clicked
  row; the expression selects every dataset row it matches, so one click can select all segments of a batch. The key
  must hit exactly the rows meant: check it with the user (a batch number may repeat per product). Guard a drag:
  apply only when the pointer moved less than 5 px. bideneb sets `selectionMode` to `advanced` when the
  specification calls the function; up to 2,500 rows can be selected in this mode. [S][B]
- Helper data (shift bands, days, ticks, legend entries, buttons) comes from `sequence` transforms or inline
  `values`, never from extra dataset rows. [B]
- A cross-filter can reload the view; signals (zoom, collapsed groups) then return to their start values. [O]

## Vega patterns that held up
- Layout in signals: `W`, `H` from `width`, `height` with a minimum (`max(420, width)`), label column
  `clamp(round(W * 0.2), 190, 280)`, plot width from the rest; no pixel constants in marks.
- Pipeline: `dataset` → one data set with formulas and filters → aggregates for domains → marks. Inside one
  transform list a formula only reads fields computed above it; a wrong order draws nothing.
- Labels only where they fit: test the pixel width of the bar against `length(text) * 6.6`.
- Tick step from pixels per hour or day; legend rows from `floor((W - 16) / 128)` columns.
- `clip` of a nested group goes into `encode.update` (`"clip": {"value": true}`).

## Limits
- 30,000 rows by default; more load in batches and may miss in PDF and PowerPoint export. [S]
- More than about 4,000 marks are slow in SVG (finding P9); the canvas renderer has no hatching.
- `$schema` stays in the file (editors and bideneb need it); the copy in the report leaves it out.
