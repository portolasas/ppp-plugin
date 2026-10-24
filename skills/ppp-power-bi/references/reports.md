# Reports

## Sources
- Model and report as text where possible: Power BI Desktop › "Save as Power BI project" (`.pbip`, model in TMDL); depending on the Desktop version a preview feature that must be switched on. [D][V]
- SharePoint as source: `SharePoint.Tables(<site>, [Implementation = "2.0", ViewMode = "All"])` is faster and returns fewer columns [D]. Filter early (status, valid pointer joins), remove unused columns, expand JSON columns with `Json.Document`.
- SharePoint Online needs no gateway; the sign-in is the dataset owner's OAuth. Plan the switch to a technical account together with the flows. [D]
- Publishing: the user publishes from Desktop into the workspace; workspace Git integration only if the tenant confirms it [O].

## Refresh
- Start the flow action "Refresh a dataset" after a successful save without waiting for the end; if a refresh is running, skip it, the next save catches up.
- Limits: Pro or shared about 8 refreshes per day, Premium or Fabric clearly more [D]. Note the confirmed limit of the tenant in the README.

## Visuals and embedding
- Standard visuals first; custom visuals only if the tenant allows them.
- Deneb (Vega-Lite) for special charts such as Gantt: specification as JSON file, field names as in the spec, mind the row limit of the visual [D]. Inside an app a Gantt view is better built in the app (skill ppp-power-apps, layout).
- Brand: the theme JSON from the skill bi-designer.
- The Power Apps "Power BI tile" shows a pinned dashboard tile, not a whole report page; open the report through a link. [D]
- Viewers need Pro or PPU unless the workspace runs on Premium P or Fabric F64 and above; smaller F SKUs still need Pro. [D]

## Tests
| Test | Expectation |
|---|---|
| Refresh | the refresh in the service succeeds; duration noted |
| Row counts | table rows = source rows after the filters |
| Time | a night of the clock change (last Sunday of March or October) shows 7 h or 9 h without a 1–2 h shift, in the service |
| Values | page values = the expectation file of the reference calculation |
| Access | a viewer without edit rights sees the report |
