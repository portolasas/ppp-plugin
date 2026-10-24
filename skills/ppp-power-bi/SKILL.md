---
name: ppp-power-bi
description: Power BI reports on SharePoint data - report as text (PBIP, TMDL), Power Query from SharePoint, refresh from flows, time in UTC with conversion to Europe/Berlin, visuals and Deneb, licences and tests. Use before building, changing or checking a report or a time calculation.
---

# Power BI

Status per statement: **[B]** observed in the tenant, **[D]** documentation, not yet confirmed here, **[O]** open, **[V]** version-dependent.

## Always
1. The report lives as text in `components/power-bi/`: model and report as PBIP (`<Name>.SemanticModel/` in TMDL, `<Name>.Report/`), Power Query functions as `m/*.pq`, Deneb specifications as `deneb/*.json`; the user pastes them and publishes from Desktop. If PBIP is not possible, the `.pbix` stays in `exchange/` and the README describes model and pages. [D][V]
2. Times are stored in UTC and converted explicitly; local "now" functions are never used ([references/time.md](references/time.md)). [D]
3. The README of `components/power-bi/` is the contract: tables, filters, joins, measures, pages with their requirements, tests.

## References
| Topic | File |
|---|---|
| Sources, refresh, visuals, embedding, licences, tests | [references/reports.md](references/reports.md) |
| Time: UTC, conversion Europe/Berlin, shifts, data state | [references/time.md](references/time.md) |
