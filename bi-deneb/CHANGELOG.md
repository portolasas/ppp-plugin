# Changelog

bi-deneb is released together with ppp and carries its version. This file lists the versions that changed bi-deneb.

## 0.27.0 (2026-11-16)
- bi-deneb is a plugin of the marketplace of ppp, optional beside the plugin ppp, and carries the version of ppp.
- The colours of the corporate design (`tokens.json`) are the file of the plugin bi-design, which lies beside
  bi-deneb in the same marketplace since this version; a test keeps the copy identical.
- Skill: a custom visual needs a requirement no standard visual meets.

## 0.1.0 (2026-11-16)
First version. Not released; proven by local renders and tests, not yet by a visual opened in Power BI Desktop.

- Tool `bideneb`: `env`, `setup`, `brand`, `fields`, `types`, `suggest`, `new`, `build`, `check`, `render`, `embed`,
  `pull`, `adopt`, `template`, `list`.
- 17 visual types generated from a brief: bar, column, stacked, pareto, line, variance, bullet, dumbbell, waterfall,
  heatmap, status, scatter, histogram, boxplot, timeline, donut, kpi; and `custom` for a hand-written specification.
- Local render with vl-convert-python (no Node, no browser): typical and stress rows in three sizes, contact sheet.
- Rules: Deneb and Power BI (D), fields (F), interaction (X), brand (B), picture (P), the visual in the report (R).
- Brand profiles `boehringer-ingelheim` (tokens of bi-design 2.12.1) and `neutral`.
- Embedding into PBIR in the form Power BI Desktop saves; the way back with `pull`; taking over existing visuals
  with `adopt`; a Deneb template for import by hand.
- Skill `bi-deneb`, agent `bi-deneb` for Claude Code and for GitHub Copilot in VS Code.
- After an independent review: `embed` and `pull` stop when report and file both changed (state kept in the brief);
  `embed` renders once before it writes, looks for a free place on the page and keeps the settings Desktop made;
  fields with an apostrophe are refused with the way out; empty labels, negative values and zero totals draw
  without errors; the local render sizes a specification the way Deneb does; named CSS colours count for B1; X3 is
  a note that says what a click on an aggregated mark selects.
