# Performance with SharePoint and flows

## Measure first
Baseline with the **Monitor** (Studio › Advanced tools › Monitor) and a stopwatch: start until usable, each screen switch, each main action, number of data calls per screen. Derive a budget from it (e.g. "start ≤ 4 s") and run the app checker (performance) after every screen build. [D]

## Delegation
- Non-delegable formulas cut results silently at the row limit (default 500, at most 2,000). [D]

  | Delegable against SharePoint | Not delegable |
  |---|---|
  | Filter, LookUp, Sort with comparisons, And, Or, Not, `StartsWith` on simple columns | `in`, `Search`, `CountRows`/`CountIf` over the list, `Distinct`, `GroupBy`, `AddColumns` over the list |

  **The delegation warning in Studio decides** and counts as an error (app checker 0).
- **Optional filters** [B] (PAPPS-20261006-MAC-01): `IsBlank(x) || StartsWith(column; x)` in a delegated query raises a delegation warning. One delegable query per combination of filled filters (`If` branches), or filter locally after loading. Comparison values from `With(…)` also raised warnings: set them into global variables first, dates as `DateTime(…)`. `ppp canvas` reports `IsBlank(x) ||` in filters on the project's lists.
- **Choice columns in delegated filters** [B] (PAPPS-20261024-WIN-01): the choice column offered only `=` to SharePoint. `Lifecycle.Value <> "Archiv"` in the Items of a searchable combo box raised a delegation warning, and the box showed empty rows (Studio kept sample search data). Join `=` with `||` over every allowed value. `ppp canvas` reports `.Value <>` in filters on the project's lists.
- **Yes/No columns in delegated filters** [B] (PAPPS-20260928-MAC-01): compare only with fixed literals (`Intern = true`); an expression on the right (`Intern = (Auswahl = "Intern")`) was rejected as an invalid query. Selection filters as complete separate branches (`Switch`).
- Lists above 5,000 items: filtered and sorted columns need an index. [D]
- Lookup, person, multi-choice and managed-metadata columns are slow and limit delegation; values filtered often (status, owner e-mail, parent key) go into simple columns, deliberately denormalised. [D]
- Keep "explicit column selection" on in the app settings. [D]

## Screens and formulas
- `App.OnStart` minimal, independent loads in `Concurrent(...)`, start screen through `App.StartScreen` [D]. Load data per screen for what is visible.
- **Collections** only for small, stable reference data or offline use, never as a copy of a large list.
- **Galleries**: no `LookUp` or `Filter` against a data source inside the template (one call per row); few controls per template; no nested galleries over large data. [D]
- A condition repeated in many `Visible`, `DisplayMode` or `Fill` properties is computed once (named formula, variable or `With`).

## Saving and flows
- Several records with one `Patch(list, table)` or one flow, not `ForAll(… Patch …)` row by row. [D]
- Flow calls have noticeable latency: never per row or in loops, one call per user action with a compact response. Long work: the flow answers early (accepted plus correlation ID), works on server-side and writes the status into the list. [D]
- Everything that must be consistent or checked runs server-side in a flow. [B]
