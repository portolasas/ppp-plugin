# Special visuals: Gantt, timelines, Deneb

Status per statement as in SKILL.md. Source: prototype of a shift timeline on a SharePoint-fed report (11.11.2026), checked by local rendering only; the Desktop test is open.

## Choice of the visual (as of 11.11.2026)
| Option | Fits | Limits | Use |
|---|---|---|---|
| Microsoft Gantt (AppSource, 3.4.9) | Parent with expand/collapse, "Group tasks" puts several bars on one row, date type down to hour, today line, legend per category | no background bands (shifts), one-line axis, little control of the look, about 1,000 rows | quick view; comparison [D][V] |
| Nova Silva PowerGantt | 10 levels, several items per row, today line | hours only through a custom date scale (own table, full years); that scale failed with parent rows in an earlier project; no shift calendar | not for shift precision [B][V] |
| Built-in Gantt (preview, October 2026) | 3 group levels, no extra visual | axis down to days | watch only [D][V] |
| **Deneb** (certified, 2.0.1) | anything drawable: shift and day axis, hatched off-time, several bars per row, labels in bars, tooltip per segment, cross-filter; specification as a file in git | Vega knowledge; expand/collapse only with Vega signals | **main path for timelines** [D][V] |
| Matrix + DAX measure returning SVG (data category Image URL) | native expand/collapse, native cross-filter, export without limits | tooltip per row only, image width limit unclear, axis header as its own SVG, long DAX strings | fallback when expand/collapse is required [D] |
| Own pbiviz visual | full freedom | Node tool chain, distribution as organisational visual, not certifiable (no PDF/PowerPoint export, no subscriptions), 10–20 person-days | only if Deneb fails [D] |
| Power Apps visual | the app's own timeline | at most 1,000 records, does not filter the report, no PDF export | no [D] |

Inside an app the timeline belongs into the app (skill ppp-power-apps).

## Data: one segment table
- One calculated table in long format: one row per phase or event with `Gruppe`, `Zeile`, `Start`, `Ende`, `Phase`, `Status`, the business key and the filter key. `Gruppe` and `Zeile` are generic, so the same specification shows e.g. line → equipment or campaign → equipment.
- Check the business key against the data and ask the user before building; an apparent key may be unique only together with another column. Check the text values of filters against the data as well.
- An open segment ends at the data state (`Datenstand`, [time.md](time.md)) only if it started within a window that is a parameter (e.g. 48 h); older open segments are left out.
- No free text that may hold person names; take a category column instead.
- Same rows as the existing visual: relate the segment table through the same key that filters the existing visual (e.g. the shift of the start), so a slicer selects the same records.
- Window measures for the visual use `CALCULATE(…, ALLSELECTED())`; a measure in a Deneb dataset is otherwise evaluated per row.
- Net and gross: existing measures may subtract non-working time; a time axis shows gross time. Name the difference in the README and test one record that spans the off-time.

## Deneb facts
- Visual GUID `deneb7E15AEF80B9E4D4F8E12924291ECE89A`, data role `dataset`; PBIR object `vega` with `provider`, `jsonSpec`, `jsonConfig`, `renderMode`, `enableTooltips`, `enableSelection`, `enableHighlight` (source: deneb-viz/deneb). [D] Whether Desktop takes a hand-written `jsonSpec` from PBIR: [O]
- Container size: signal `denebContainer.width` / `denebContainer.height` from 2.0; `pbiContainerWidth`/`Height` are migrated with a warning. [D][V]
- Patterns for hatching: `fill: "url(#diagonal-stripe-1)"` and further ids of the Deneb pattern registry. [D]
- 30,000 rows by default; more rows load in batches but are not guaranteed in PDF/PowerPoint export. [D]
- Cross-filter works only if the specification keeps the dataset rows; generate helper data (shifts, days, ticks) inside the specification with a `sequence` transform. [D]
- How Deneb passes date/time values (local wall time or UTC) [O]; convert with `time(toDate(...))` and test one value against the table.
- For a timeline prefer Vega over Vega-Lite: own layout, multi-row header, container size, signals for later interaction. Build shift times with `datetime(y, m, d, h, mi)` (safe over the clock change), row and group index with `window`, labels only when the bar is wide enough, tick step by pixels per hour.

## Microsoft Gantt in PBIR [O]
GUID `Gantt1448688115699`; roles `Task`, `Parent`, `Legend`, `StartDate` (grouping), `EndDate` (measure, e.g. Max = `Function: 4`), `ExtraInformation`; objects `general.groupTasks`, `dateType.type` (`Second` … `Year`), `dateType.showTodayLine` (source: microsoft/powerbi-visuals-gantt).

## Check before Desktop
- `ppp pbi check` checks references and names, not DAX semantics.
- A local preview shortens the loop: rebuild the table logic in Python on the source exports and render the specification with vega-embed in the browser pane, injecting `dataset`, `denebContainer` and the pattern, in three sizes. The rebuild is a second implementation and only an approximation of the DAX; the Desktop test stays required.
- Preview data from real exports stays in the scratchpad, never in git or an artifact.
- AppSource visuals in PBIR: list them in `publicCustomVisuals` of `report.json`; look up GUID, role and property names in the visual's public repository instead of guessing.
