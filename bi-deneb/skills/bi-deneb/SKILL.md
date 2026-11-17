---
name: bi-deneb
description: Deneb visuals for Power BI in the brand design - build a custom visual (Vega-Lite or Vega) from a brief with the generator bideneb, render it locally with invented rows, check it (fields, Deneb rules, brand colours, contrast, overlapping or cut text) and embed it into a Power BI project (PBIP, PBIR). Use when a report needs a chart the standard visuals do not give, when a Deneb visual is to be created, changed, checked or improved, or when a Deneb specification is to be taken from or written into a report.
---

# Deneb visuals with bideneb

`bideneb` is the tool of this skill: `<plugin>/tools/bideneb.py`, `<plugin>` two folders above this file. Windows
`python "<plugin>\tools\bideneb.py" <command>`, macOS `python3 …`; without `-I`, which hides the packages of
`pip --user`. `bideneb env` prints the call with full paths: use that line afterwards.

The **brief** (`deneb/<name>.brief.json`) is the source of a visual: type, fields, options. `bideneb` generates the
specification and the config from it, renders them and checks them. Change the brief, not the generated files.

Call bideneb from the folder that holds the `.pbip` (in a ppp project `components/power-bi/`): `new` writes into
`deneb/` there, finds the report next to it, and the other commands find a brief by its name.

**A custom visual needs a reason.** A report is built from the standard visuals of Power BI; Deneb stands where a
named requirement cannot be met by one of them (several bars per row on a time axis, a bullet, a box plot, marks
the format pane does not offer). If a standard visual with one more measure shows what the user asked for, say so
and propose it instead. In a ppp project the README of `components/power-bi/` records the requirement and the
standard visual that fell short.

## Steps

1. **Start.** `bideneb env`. Done when the line `renderer` names a version and the line `brand` names the
   corporate design. Renderer MISSING: ask the user whether `bideneb setup` may install it (pip --user, no virtual
   environment); without it only the static rules run, and you say so in the hand-over. The neutral profile is the
   user's decision, never the silent default.

2. **Read the model.** `bideneb fields <project>` (the folder with the `.pbip`); `bideneb list <project>` shows the
   Deneb visuals that exist. Metadata only: never open row data, exports or `.pbi/cache.abf`. Done when every value the
   visual shows has a table and a field, or you know which measure is missing.

3. **Ask once, only what the model cannot tell you.** One bundled round with the question tool, your recommendation
   first:
   - what the reader should see at a glance (the question the visual answers) – always;
   - the fields, where several fit; the reference (plan, target, previous period) for a comparison;
   - the page of the report, and whether a click should filter the other visuals;
   - for values with a meaning (a phase, a product) the brand token of each, unless the report already has them.
   You decide the rest and name it in the hand-over: the type (`bideneb suggest <Table[Field]>…`, then the `use` and
   `avoid` lines of `bideneb types`), the title (the answer the visual gives, not the field names), formats (they
   come from the model), sizes. A value that needs a sum, a share or "the latest" is a **measure**: propose the DAX
   and add it to the model with the user's consent; the specification does not aggregate.

4. **Build.** `bideneb new <type> <name> --field role="Table[Field]" … --title "…"`; `--sample "Field=a|b|c"` gives
   the preview category names the user knows (invented or named by the user, never read from data). Done when the
   command ends with a `RESULT` line.

5. **Look and improve.** Read the contact sheet `deneb/_preview/<name>_sheet.png`: typical rows and stress rows in
   three sizes, two rows and no rows in the first. Judge it against the user's question: does the eye land on the answer first? Then the findings:
   every ERROR and WARNING gets a fix or a reason; a finding that only the stress rows cause gets a judgement
   whether real data can get there. Fix through the brief (`bideneb types <type>` lists the options), then
   `bideneb build <name>`. Done after a build without errors whose picture you have looked at; at most three
   rounds, then report what stays open.

6. **No type fits** (shift bands, zoom, own layout): `bideneb new custom <name> --provider vega|vegaLite --field …`
   writes a scaffold in the brand design; you write the specification, `bideneb check <name>` renders and checks it.
   Read [references/custom.md](references/custom.md) first. Own invented rows go into `deneb/<name>.data.json`.

   **Live test.** For a custom specification, and for any specification with signals, run `bideneb live <name>`
   before step 7: it writes `deneb/_preview/<name>_live.html`, which runs the specification in Deneb's Vega version
   with data changes as slicers make them and with the states a click reaches (a page, a sort: taken from signals
   with event handlers; others go into the brief as `"live": {"states": [{"page": 3}]}`). Open it with your browser
   tool (a local file may need a small static server) and read `#result`; without a browser tool the user opens it.
   Done at `RESULT: 0 error(s)`. An error is a visual that can turn empty in Power BI; 0 errors proves these
   scenarios, not Desktop.

7. **Embed.** Ask the user to close the project in Power BI Desktop first: Desktop does not see files change
   under it and writes its own state over them when it saves. Then `bideneb embed <name> --page "<page>"` (or
   `--new-page "<name>"`). It writes `visual.json` into a free place of the page, registers Deneb in `report.json`
   and checks the result. Done when its `RESULT` shows no error; a finding R9 (the visual lies over others) goes
   to the user with the page. In a ppp project run `ppp pbi check` afterwards and commit as ppp does.

8. **Hand over.** Tell the user: the picture, the decisions you made, every finding left open, the block
   `NOT PROVEN BY THE LOCAL RENDER`, and the checks in Power BI Desktop from
   [references/desktop.md](references/desktop.md). The visual counts as done when the user has opened it in Desktop.

## Other entries

| The user wants | Do |
|---|---|
| a Deneb visual of a report checked or improved | `bideneb adopt <report> <visual>` makes brief and files from it, then steps 5 to 8 |
| a change made in the Deneb editor kept | `bideneb pull <name>`: the file takes the version of the report; the brief becomes type `custom` |
| the visual without writing into the report | `bideneb template <name>`: a Deneb template the user imports and maps by hand |
| one state to look at | `bideneb render <name> --size 400x300 --scenario stress`, `--selected 0,2` shows a cross-filter selection, `--data rows.json` own invented rows |

## Rules

- **Brand.** Colours, fonts and sizes come from the brand profile (`bideneb brand`): the corporate design, with
  the same colour values as the plugin bi-design. A colour outside it is an error (B1) that stops `embed`: write the
  token the finding names. A colour with a meaning of the business (a phase, a product) is a brand token the user
  chooses: propose brand tokens, chart order first, in the question of step 3, the same as in the other visuals of the
  report, and record the choice in the README. Colours the report already uses outside the brand go into that
  proposal; one stays only on the user's explicit word, kept in the brief: `"colours": {"#1FBB3E": "Mahlen (Nutzer,
  Datum)"}`.
- **Background.** The visual sits on the surface of its page. With `report.page` in the brief (`bideneb new …
  --page`) bideneb reads the page colour, draws for it (on Dark Green with the dark roles: `bideneb brand
  --background #08312A`) and `embed` writes it as the box of the visual; the theme otherwise draws a white box, also
  on a dark page. `"background"` in the brief only for a page not yet in the report. R11 names a visual that does
  not sit on its page.
- **Grain.** The visual gets one row per combination of its grouping fields. Every field in the brief changes the
  rows: add what is drawn, nothing else (finding F2).
- **Files.** Specification and config are files next to the brief; the copy in the report is written by
  `bideneb embed`. `visual.json` is never edited by hand: its text literals need exact quoting.
- **Pages.** A visual copied from another page keeps its `parentGroupName`; Desktop drops it on save when the group
  is not on the new page (finding R10). Replacing a visual: rename it in `visualInteractions` of `page.json` too.
- **Two sides.** When `embed` or `pull` stops because the report and the file both changed, the user decides which
  side wins; `--force` only after their answer.
- **A generated specification stays generated.** To go beyond the options of a type, set `"type": "custom"` in the
  brief: the file is then yours and `bideneb build` only checks it.
- **Findings** name their fix. Codes: D Deneb and Power BI, F fields, X interaction, B brand, P picture, R report.
  [references/findings.md](references/findings.md) explains a code when the line does not suffice.
- **Questions** go through the question tool, bundled, recommendation first. Conflicts between what the user says
  and what the model holds are asked, never settled silently.
