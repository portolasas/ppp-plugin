# PBIP: model and report as text

Sources: Microsoft Learn, [PBIP overview](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview), [report folder](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report) and [external editing](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-external-editing), all 23.09.2026; [TMDL](https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-overview). Checked on 06.11.2026 (PLUGIN PL-22).

## Folders
```
components/power-bi/
├── <Name>.pbip
├── <Name>.SemanticModel/
│   ├── definition.pbism
│   ├── definition/            model.tmdl, relationships.tmdl, expressions.tmdl, tables/<Table>.tmdl, cultures/, roles/
│   └── .pbi/                  cache.abf (imported data), localSettings.json: never in git
└── <Name>.Report/
    ├── definition.pbir        datasetReference byPath "../<Name>.SemanticModel"
    ├── definition/            report.json, version.json, reportExtensions.json, pages/pages.json,
    │                          pages/<page>/page.json, pages/<page>/visuals/<visual>/visual.json, bookmarks/
    └── StaticResources/       themes and images; each resource has its entry in definition/report.json
```
- PBIP and PBIR are GA; PBIR is the default report format since September 2026. Desktop converts a PBIR-Legacy report (`report.json` instead of `definition/`) to PBIR at the next save. [D][V]
- An older project may keep the model as `model.bim` (TMSL). `ppp pbi` reads it; edit TMDL. [D][V]
- Files edited by Desktop only: `definition.pbir`, legacy `report.json`, `mobileState.json`, `semanticModelDiagramLayout.json`, `diagramLayout.json`, auto date tables (`LocalDateTable_*`). [D]
- Each file path stays under 260 characters under Windows, and the project folder lies outside OneDrive and SharePoint. [D]

## Round trip with Desktop
1. The user saves in Desktop before the agent edits; Desktop writes its state to the files only on save. [D]
2. The agent edits, then runs `ppp pbi check`.
3. Desktop from the August 2026 release with the preview feature "Detect and reload external PBIP changes" shows a banner **Apply external changes** and reloads model and report; otherwise the user closes and reopens the project. Renamed files or folders always need a restart. Unsaved changes in Desktop are overwritten by the reload. [D][V]
4. If the model folder holds `unappliedChanges.json`, the user applies the pending query changes in Desktop first; otherwise Desktop discards the external expression changes. [D]
5. Desktop reports **blocking errors** (schema, missing required property; it names the file) and fixes **non-blocking** ones itself (e.g. `activePageName`). The user reports both; the agent fixes the file. [D]

## TMDL (model)
- Indent with tabs, one tab per level; properties one level below their object, a multi-line expression two levels below. [D]
- Names with spaces or special characters (`. = : '`) in single quotes, a quote doubled: `measure 'Total Amount' = SUM(Sales[Amount])`. [D]
- Objects: `table`, `column` (with `= <DAX>` a calculated column), `measure`, `hierarchy` with `level`, `partition <name> = m` with `source =` (the Power Query), `relationship <id>` with `fromColumn: Table.Column` and `toColumn:` in `relationships.tmdl`, shared queries and parameters as `expression` in `expressions.tmdl`. [D]

## PBIR (report)
- Every file is JSON with `$schema` at the top, UTF-8 without BOM; the schemas are public in `microsoft/json-schemas/fabric/item/report/definition`. [D]
- Names of pages, visuals and bookmarks (folder or file and the `name` property) consist of letters, digits, `_` and `-`; otherwise Desktop ignores the object. Renaming breaks references and needs a restart. [D]
- A field is bound as `{"Column" | "Measure": {"Expression": {"SourceRef": {"Entity": "<Table>"}}, "Property": "<Name>"}}`, wrapped in `Aggregation` or `HierarchyLevel` where needed. Entity and property must exist in the model; the schema check in VS Code does not see this, `ppp pbi check` does (R7). [D]
- Each filter in `filterConfig.filters` has a `name`; each `pageBinding.name` is unique in the report. [D]
- A new visual: copy a `visual.json` that Desktop wrote for the same visual type, give it a new name and folder, and change only `position` and the field bindings. [O] whether hand-written formatting passes Desktop: check on the company computer.
- Report-level measures live in `reportExtensions.json`. [D]
- Filter values, slicer selections and series formatting carry data values into `visual.json` and bookmarks; check them before a commit when the data is confidential. [D]
- A copied bookmark keeps only the visuals that exist on its page. [D]
