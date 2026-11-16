# Findings

Levels: ERROR stops `bideneb embed`; WARNING gets a fix or a reason in the hand-over; NOTE is for your judgement.
`bideneb check` renders the scenarios typical and stress in every size, few (two rows) and empty (no rows) in the
first. A finding prefixed `[stress …]` comes from rows that are extreme on purpose (14 categories, long names, an outlier,
a zero, an empty value): decide whether the real data can get there, and say so.

## D – Deneb and Power BI (read from the specification)
| Code | Meaning | Fix |
|---|---|---|
| D1 | no data source `dataset` | Vega-Lite `"data": {"name": "dataset"}`; Vega an entry `{"name": "dataset"}` |
| D2 | a `url` that is not a `data:` URI | Deneb loads nothing from outside; bring it through the dataset or inline `values` |
| D3 | `__identity__`, `__key__` | removed in Deneb 1.9; use `__row__` |
| D4 | `pbiContainerWidth`, `pbiContainerHeight`, `pbiContainer` | `denebContainer.width`, `.height`, `denebContainer` |
| D5 | fixed size | leave `width`/`height` out, or derive from `denebContainer` |
| D6 | `utc…` functions or time units | dates are local time; use the local functions |
| D7 | pattern fill with `renderMode` canvas | SVG, or no hatching |
| D8 | `width`, `height`, `autosize` in the config | set them in the specification; Deneb drops "container" sizes and `autosize.resize` from the config |
| D9 | unknown `pbi…` function | Deneb has pbiColor, pbiFormat, pbiFormatAutoUnit, pbiPatternSVG, pbiCrossFilterApply, pbiCrossFilterClear |
| D10 | d3 number formats | `formatType: "pbiFormat"` with the format of the measure |
| D11 | theme colours (`pbiColor`, `pbiColor…` schemes) | brand hex values, unless the report theme is the brand theme |
| D12 | no `$schema` in the file | add the Vega or Vega-Lite schema URL |

## F – fields
| Code | Meaning | Fix |
|---|---|---|
| F1 | a field the dataset does not have and no transform creates | the key in the finding; a renamed field needs `"as"` in the brief |
| F2 | a dataset field nothing uses | remove it from the brief: it splits rows or costs a query |

## X – interaction
| Code | Meaning | Fix |
|---|---|---|
| X1 | cross-filter on, `__selected__` unused | opacity 0.3 where `__selected__ == 'off'` |
| X2 | `pbiCrossFilterApply` without clear | a click on the empty area calls `pbiCrossFilterClear()` |
| X3 | cross-filter on, marks from aggregated rows | a click selects every row with the mark's field values; keep the grouping fields on the mark, or aggregate in a measure, or `"crossFilter": false` |
| X4 | `__selected__` read, cross-filter off | `"crossFilter": true`, or remove the reading |
| X5 | no tooltip | `tooltip` on the mark or in `encode` |

## B – brand
| Code | Meaning | Fix |
|---|---|---|
| B1 | a colour that is not a token: a hex value, a CSS name, `hsl()`, or one drawn by a default of Vega | the token the finding names; a colour with a business meaning: ask the user and keep the answer in the brief, `"colours": {"#1FBB3E": "Mahlen, Farbe des Berichts"}`: the finding becomes one NOTE. Defaults of Vega: set them in the config |
| B2 | another font | `config.font` of the brand |
| B3 | a font size off the brand scale | sizes of the scale in the config; below the smallest size is a WARNING |
| B4 | corner radius above the brand limit | 0 to the limit |
| B5 | gradient or shadow | flat colour |
| B6 | text in a colour the brand forbids for text | the text or secondary text colour; on a fill the text colour of that fill |
| B7 | thin line or small marker in a colour too weak on light | a colour of the `line` palette |
| B8 | a large area in a signal colour | status fill colours; signal colours for dots with a label |

## P – picture (read from the render)
| Code | Meaning | Fix |
|---|---|---|
| P0 | not rendered | `bideneb setup` |
| P1 | Vega did not compile or reported an error | the message names the expression, signal or data set |
| P2 | nothing drawn from the rows | field keys, filters, scale domains; with own rows: their values |
| P3 | larger than the container | sizes from `denebContainer`; Vega-Lite without fixed size |
| P4 | text outside the container | label limit, room (padding, an invisible mark that widens the domain), or inside the mark |
| P5 | text cut with an ellipsis | higher limit, more room, shorter names in the model |
| P6 | texts overlap | fewer labels, a condition on the available width, `labelOverlap` |
| P7 | text contrast too low | the text colour the finding names for that fill |
| P8 | more legend entries than colours, or more than seven | group small categories in the model, or another type |
| P9 | more than 4,000 marks | fewer rows, or canvas |
| P10 | bars thinner than 1.5 px | filter, aggregate, larger visual |

## R – the visual in the report
| Code | Meaning | Fix |
|---|---|---|
| R0 | not embedded yet, or the report is not PBIR | `bideneb embed`; save the report as Power BI project |
| R1 | Deneb missing in `publicCustomVisuals` | `bideneb embed` |
| R2 | a property in the wrong literal form | `bideneb embed` rewrites the properties |
| R3 | `jsonSpec` or `jsonConfig` is not JSON | `bideneb embed`, or repair in the Deneb editor and `bideneb pull` |
| R4 | `denebMetaVersion` is not `'2'` | `bideneb embed` |
| R5 | projections and brief differ, or a field with an implicit aggregation | add the field to the brief, or `bideneb embed`; replace an implicit aggregation by a measure |
| R6 | report and file differ | `bideneb embed` (file wins) or `bideneb pull` (report wins): ask when unsure who changed it |
| R7 | selection settings differ from the brief | `bideneb embed` |
| R8 | the visual is very small on the page | resize in Desktop or `--position` |
| R9 | the visual lies over other visuals of the page | the user moves it in Desktop, or `bideneb embed --position x,y,width,height`, or a new page |
| R10 | a visual of the page belongs to a group that is not on the page, or `visualInteractions` name a visual that is not there | remove `parentGroupName` (or copy the whole group); rename or remove the interaction. Desktop drops such a visual when it saves: slicers copied from another page vanished this way |

## L – the live test (`bideneb live`, in a browser with Deneb's Vega)
| Code | Meaning | Fix |
|---|---|---|
| L0 | the test page failed (Vega did not load, the specification did not parse) | the message; without internet the page cannot load Vega |
| L1 | after a data change a running view draws other marks than a fresh embed of the same rows | a signal kept a state from the old rows (a page, an offset, a selection): derive it from the data, e.g. `clamp(page, 0, pages - 1)`, instead of resetting it on an event |
| L2 | nothing drawn from rows | as P2, but in Deneb's Vega version |
| L3 | a state a click reaches (from the signals with handlers, or `"live": {"states": [...]}` of the brief) draws nothing after the rows got fewer; WARNING: the state could not be set | as L1: derive the state from the data (`clamp`); for a WARNING remove the state from the brief |
| L4 | Vega reported an error or warning while running | the message names the expression, signal or data set |
