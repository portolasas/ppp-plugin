---
name: ppp-power-bi
description: Power BI reports on SharePoint data - report as PBIP text (TMDL model, PBIR report) with ppp pbi list and check, Power Query from SharePoint, refresh from flows, time in UTC with conversion to Europe/Berlin, brand design of a report, standard visuals before custom visuals (Deneb, optional plugin bi-deneb), licences and tests. Use before reading, building, designing, changing or checking a report, a page, a visual, a .pbix or a time calculation.
---

# Power BI

Status per statement: **[B]** observed in the tenant, **[D]** documentation, not yet confirmed here, **[O]** open, **[V]** version-dependent.

## Always
1. **PBIP is the only working format.** The report lives in `components/power-bi/` as `<Name>.pbip`, `<Name>.SemanticModel/` (TMDL) and `<Name>.Report/` (PBIR); Power Query functions as `m/*.pq`, Deneb specifications as `deneb/*.json`. A `.pbix` is input only: a card asks the user to open it in Desktop and save it with File › Save as › Power BI project (.pbip) into that folder, on a short path outside OneDrive and SharePoint. [D]
2. **Round trip:** `ppp pbi list` before reading the files; edit TMDL and PBIR as text; `ppp pbi check` until it reports no error; then a card: apply the external changes in Desktop (or reopen the project), report blocking errors, save, publish. Rules and pitfalls of the formats: [references/pbip.md](references/pbip.md).
3. **Metadata only.** The agent reads model, queries and report definitions, never row data. `.pbi/cache.abf` holds the imported data and stays out of git (`ppp check` reports a missing `.gitignore` line).
4. Times are stored in UTC and converted explicitly; local "now" functions are never used ([references/time.md](references/time.md)). `ppp pbi check` finds them. [D]
5. The README of `components/power-bi/` is the contract: tables, filters, joins, measures, pages with their requirements, custom visuals with their reason, tests.
6. **Brand design, always.** Every report carries the brand theme of the skill bi-designer (plugin bi-design); colours, fonts and layout come from it. Without bi-designer in your skill list (Claude Code names it `bi-design:bi-designer`) a card comes before any page is designed. `ppp pbi check` reports a report without a custom theme (R10). One surface per report, white or Dark Green, on every page and in every visual; colours with a meaning are brand tokens (R13 to R15). ([references/design.md](references/design.md))
7. **Standard visuals first.** A page is built from the standard visuals of Power BI. A custom visual (Deneb) stands only where a named requirement cannot be met by a standard visual, and the README names that requirement. It is then built with the optional plugin bi-deneb, **if the skill `bi-deneb` is in your skill list** (Claude Code names it `bi-deneb:bi-deneb`); if not, a card, never an assumption. ([references/design.md](references/design.md))

## References
| Topic | File |
|---|---|
| PBIP: folders, TMDL and PBIR rules, external editing, pitfalls | [references/pbip.md](references/pbip.md) |
| Sources, refresh, embedding, licences, tests | [references/reports.md](references/reports.md) |
| Design: brand theme, choice between standard and custom visual, the optional plugin bi-deneb | [references/design.md](references/design.md) |
| Time: UTC, conversion Europe/Berlin, shifts, data state | [references/time.md](references/time.md) |
| Gantt and timelines: choice of visual, segment table, Deneb facts, a specification by hand | [references/visuals.md](references/visuals.md) |
