# Changelog

bi-deneb is released together with ppp and carries its version. This file lists the versions that changed bi-deneb.

## 0.27.4 (2026-11-17)
From SEQONIS 17.11.: on a dark green page the Deneb visual stayed white (the theme draws a white box behind a visual
without its own background), and its phase colours were not colours of the brand: B1 was a warning, left open.
- The page decides the surface: with `report.page` in the brief bideneb reads the page colour (canvas over wallpaper,
  the defaults of Power BI, the theme; module `surface.py`, the same file as in ppp) and draws for it. A dark page
  takes the dark roles of the brand (`charts.json` "dark": text White, focus Accent Green, chart colours with at
  least 4.4:1 on Dark Green); `bideneb brand --background #08312A` shows them. Every type draws clean there.
- `embed` writes the page colour as the box of the visual and refuses a visual drawn for the other surface before
  it creates a page (`--force` writes it and names the error); `--new-page` copies background and wallpaper of the
  report; a colour the user accepted in the brief (`colours`) does not stop `embed`.
- R11: the visual does not sit on its page (drawn for the other surface; its box or a background of the
  specification of the other surface).
- B1 is an ERROR and stops `embed`; a colour the user keeps on their explicit word goes into the brief (`colours`).
- B6 judges text on the page only (text on a fill: P7); B7 knows dark pages and skips lines of width 0 (a legend
  rule of width 0 counted as a thin line).
- Box plot: a collapsed median (one value) was drawn in the default colour of Vega-Lite; the config of Vega-Lite
  sets the mark colour of the brand.
- SKILL.md › Brand and Background, custom.md › Colour, findings.md (B1, B6, B7, R11).

## 0.27.1 (2026-11-16)
From SEQONIS package 006: two custom visuals were empty when the user first opened them in Desktop, and their
slicers were gone after the save. The cause of the empty visuals is open (a copy without data before a refresh, or no size
on the first embed: neither is proven); the session then reproduced a second fault in a browser: after paging, fewer rows drew nothing.
- `bideneb live <name>`: a test page that runs the specification in Deneb's Vega version (6.4.0, from jsDelivr) in a
  browser. It embeds every scenario fresh and changes the data of one running view as slicers do; both must draw the
  same. Then it sets the states a click reaches (other values of signals with event handlers, plus states of the
  brief) and narrows the rows. Findings L0 to L4. Against the faulty first-round spec it reports L3 without any state
  in the brief; against its repair it reports nothing.
- Scenarios `few` (two rows) and `empty` (no rows); `bideneb check` renders them in the first size.
- R10: a visual of the page belongs to a group that is not on the page (Desktop drops it on save), or
  `visualInteractions` name a visual that is not there; ppp pbi check has the same rule for every report (R12).
- X3 no longer counts `fold` as aggregating: folded rows keep `__row__` (shown in Vega 6.4.0).
- Brief `"colours"`: colours outside the brand that the user decided on; their B1 becomes one NOTE.
- F1 ignores marks drawn from another mark (reactive geometry); their datum is a scene item.
- The config of a custom Vega visual names the font for axes, legend and title (Vega has no top-level font).
- custom.md: state from the data instead of signal events, size from `denebContainer`, empty datasets, label
  backgrounds; desktop.md: empty copies without cache, vanished slicers, empty after a filter change.

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
