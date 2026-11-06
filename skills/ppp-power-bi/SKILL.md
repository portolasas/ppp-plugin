---
name: ppp-power-bi
description: Power BI reports on SharePoint data - report as PBIP text (TMDL model, PBIR report) with ppp pbi list and check, Power Query from SharePoint, refresh from flows, time in UTC with conversion to Europe/Berlin, visuals and Deneb, licences and tests. Use before reading, building, changing or checking a report, a .pbix or a time calculation.
---

# Power BI

Status per statement: **[B]** observed in the tenant, **[D]** documentation, not yet confirmed here, **[O]** open, **[V]** version-dependent.

## Always
1. **PBIP is the only working format.** The report lives in `components/power-bi/` as `<Name>.pbip`, `<Name>.SemanticModel/` (TMDL) and `<Name>.Report/` (PBIR); Power Query functions as `m/*.pq`, Deneb specifications as `deneb/*.json`. A `.pbix` is input only: a card asks the user to open it in Desktop and save it with File › Save as › Power BI project (.pbip) into that folder, on a short path outside OneDrive and SharePoint. [D]
2. **Round trip:** `ppp pbi list` before reading the files; edit TMDL and PBIR as text; `ppp pbi check` until it reports no error; then a card: apply the external changes in Desktop (or reopen the project), report blocking errors, save, publish. Rules and pitfalls of the formats: [references/pbip.md](references/pbip.md).
3. **Metadata only.** The agent reads model, queries and report definitions, never row data. `.pbi/cache.abf` holds the imported data and stays out of git (`ppp check` reports a missing `.gitignore` line).
4. Times are stored in UTC and converted explicitly; local "now" functions are never used ([references/time.md](references/time.md)). `ppp pbi check` finds them. [D]
5. The README of `components/power-bi/` is the contract: tables, filters, joins, measures, pages with their requirements, tests.

## References
| Topic | File |
|---|---|
| PBIP: folders, TMDL and PBIR rules, external editing, pitfalls | [references/pbip.md](references/pbip.md) |
| Sources, refresh, visuals, embedding, licences, tests | [references/reports.md](references/reports.md) |
| Time: UTC, conversion Europe/Berlin, shifts, data state | [references/time.md](references/time.md) |
