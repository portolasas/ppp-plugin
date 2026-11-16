# bi-deneb

bi-deneb is an optional agent plugin for **VS Code (GitHub Copilot)** and **Claude Code**, distributed in the
marketplace of ppp. It builds, checks and improves **Deneb visuals for Power BI** in a brand design: from "I need a
chart that shows …" to the visual in the report.

It is a plugin of its own: install it only if you build custom visuals. ppp works without it and checks whether its
skill is there before it relies on it. bi-deneb also works without ppp, in any folder with a Power BI project (PBIP).

## When to use it
A report is built from the standard visuals of Power BI. A Deneb visual stands where a requirement cannot be met by
one of them: several bars per row on a time axis, a bullet, a box plot, marks the format pane does not offer.

## What you get
- **Skill and agent `bi-deneb`**: read the model (metadata only), ask once what the model cannot tell, build, look,
  improve, embed, hand over.
- **Tool `bideneb`** (Python): 17 visual types from a brief (bar, column, stacked, pareto, line, variance, bullet,
  dumbbell, waterfall, heatmap, status, scatter, histogram, boxplot, timeline, donut, kpi) and `custom` for a
  specification written by hand; a local render with invented rows in three sizes; checks of fields, Deneb rules,
  brand colours, contrast and overlapping or cut text; a live test page that runs the specification in Deneb's Vega
  version with data changes (`bideneb live`); embedding into the report (PBIR) and the way back.
  `bideneb types` lists them with what each is for.

## Install
Add the marketplace of ppp if it is not there yet (`portolasas/ppp-plugin`), then install **bi-deneb** from it.
VS Code: Customizations › Browse, or the Extensions view under Agent Plugins; then "Developer: Reload Window".
Claude Code:
```
/plugin install bi-deneb@ppp
```
The renderer is optional and installed on request: `python "<plugin>/tools/bideneb.py" setup` installs
`vl-convert-python` and Pillow with `pip --user` (no virtual environment). Without it only the static rules run.
Call the tool without `-I`.

## Brand design
A visual is drawn in a brand profile. The plugin carries the corporate design of Boehringer Ingelheim
(`brands/boehringer-ingelheim/`: `tokens.json` with the colours, the same file as in the plugin **bi-design**, and
`charts.json` with the role each token plays in a chart) and a profile `neutral`. The theme of the report, the page
layout and the logo belong to the skill bi-designer of the plugin bi-design, a third plugin of this marketplace.

## What the local render does not prove
The rows are invented, the functions Deneb adds (`pbiFormat`, `pbiColor`, cross-filter) are emulated, and the
renderer runs a slightly older Vega than Deneb. A visual counts as done when you have opened it in Power BI Desktop;
the skill hands you the checks for that.

What changed: [CHANGELOG.md](CHANGELOG.md).
