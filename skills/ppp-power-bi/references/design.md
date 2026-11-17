# Design of a report: brand theme, standard visuals, custom visuals

Status per statement as in SKILL.md. Decided by the user on 16.11.2026 (PLUGIN PL-24, PL-25).

## Brand design, always
- Every report is built in the corporate design. The source is the skill **bi-designer** (plugin bi-design): its Power BI section in `reference/plattformen.md` and the ready theme `marken/<brand>/powerbi-theme.json`.
- **bi-designer is not in your skill list** (Claude Code lists plugin skills with their plugin, here `bi-design:bi-designer`)**:** a card asks the user to install the plugin bi-design before a page is designed; it is an optional plugin of the marketplace of ppp, like bi-deneb (Claude Code: `/plugin install bi-design@ppp`). A neutral look is the user's decision on that card, recorded in the README; it is never the silent default.
- **The theme comes into the report through Desktop:** a card with the path of the theme file, "View › Themes › Browse for themes", save. Desktop then stores the file under `<Name>.Report/StaticResources/RegisteredResources/` and names it in `report.json` as `themeCollection.customTheme` with an item in `resourcePackages` (read from a report Desktop saved, 11.2026). [B] Writing that registration by hand is untested [O]; use the card.
- `ppp pbi check` reports a report without a custom theme as **R10**. It cannot tell whether the theme is the brand theme: compare the file under `RegisteredResources/` with the one of bi-designer when in doubt.
- Colours, fonts and sizes come from the theme. A visual gets its own formatting only for what the theme cannot express (a status colour bound to a value, an emphasised series), and then with a colour of the theme (theme colour reference) or the hex value of a named token of bi-designer. Page layout, titles and the logo follow bi-designer.
- **A colour with a meaning** (a phase, a product, a reason) is a brand token of bi-designer, from the chart order first, the same token on every page and in every visual, Deneb included; a measure that returns colours for conditional formatting returns token hex values, each carrying the label colour on it (3:1 at least). Which token stands for which meaning is the user's decision, asked once with a proposal and recorded in the README. The colours an older report brings along are no decision: they go to the user with the proposal. [B SEQONIS 17.11.]

## One background per report
- A report has one **surface** on every page, chosen once by the user and recorded in the README: **white** (page and boxes White, text Dark Green, Accent Green only as a fill; the default of bi-designer) or **Dark Green** (page and boxes Dark Green, text White, Accent Green for highlight and selection).
- The page shows its canvas over its wallpaper; a canvas without its own transparency is 100 % transparent, so the wallpaper (`outspace` in `page.json`) decides. [D] A new page copies `background` and `outspace` from a page of the report.
- Every visual sits on its surface: its box (`visualContainerObjects.background`) carries the page colour or is off, its text the text colour of the surface. A visual copied from another page or report brings its old colours: set them with the copy. A custom visual shows the white box of the theme until its background is set; `bideneb embed` sets the page colour and draws the visual for the page.
- `ppp pbi check`: **R13** pages of one report on both surfaces, **R14** a box of the other surface than its page, **R15** text that does not stand on its background (title, axes, legend, text box, slicer items, cards, tables). [B SEQONIS 17.11.: light pages among dark green ones, a white Deneb visual and white slicers on a dark page]

## Standard visuals first
A page is built from the standard visuals of Power BI, formatted by the theme. They export, filter, drill, sort and scale without extra effort, need no tenant setting, and every colleague can maintain them in Desktop.

| The reader should see | Standard visual |
|---|---|
| one figure, with or without a target | card, KPI, gauge |
| a ranking or a comparison of categories | clustered bar or column chart |
| parts of a whole over categories | stacked or 100 % stacked bar or column chart |
| a trend | line or area chart; line and column chart for two measures |
| the same chart per category | small multiples of the bar, column, line or area chart |
| a bridge from a start to an end value | waterfall chart |
| two measures per item | scatter chart |
| few shares of one whole | donut or pie chart (up to about five slices), treemap |
| a cross table, with a heat scale or status marks | matrix or table with conditional formatting (background colour, icons, data bars) |
| the largest causes with their cumulated share | line and column chart with a measure for the cumulated share |
| a distribution | column chart over a bin column of the model |
| a choice by the reader | slicer |

Before a custom visual, try the standard visual with a measure or a column added to the model: most "special" charts are a standard chart plus one calculation.

## A custom visual only for a named requirement
A custom visual (Deneb) stands where a requirement cannot be met by any standard visual, for example:
- several bars per row on a time axis, with bands for shifts or off-time (timeline, Gantt);
- a value against a target with quality ranges in one row (bullet), the change between two states per category (dumbbell), a distribution as box plot;
- marks, labels or a layout the format pane does not offer and the requirement demands.

"Looks nicer", "more modern" or "we can" is no requirement. In doubt, put both options on a card: the standard visual with what it cannot show, the custom visual with its cost (Deneb must be allowed in the tenant, a specification to maintain, a Desktop test of its own).

**Record.** The README of `components/power-bi/` lists every custom visual with its page, the requirement, the standard visual that fell short and why, and its brief (`deneb/<name>.brief.json`). `ppp pbi check` names the Deneb visuals of a report as **R11**, so that each one can be held against that list.

## Building a Deneb visual: the plugin bi-deneb is optional
bi-deneb is an optional plugin of the marketplace of ppp. It is installed and enabled separately; ppp works without it. Check, never assume:

1. **Is the skill `bi-deneb` in your skill list?** (Claude Code names it `bi-deneb:bi-deneb`.) That is the check: the tool `bideneb` lies in the marketplace copy even when the plugin is not enabled, so finding the file proves nothing.
2. **Yes:** follow the skill bi-deneb from its first step. It reads the model, asks once, generates the specification from a brief, renders it locally with invented rows, checks fields, Deneb rules, brand and legibility, and embeds the visual. In a ppp project its files lie in `components/power-bi/deneb/`; after `bideneb embed` run `ppp pbi check`, add the visual to the README (Record, above) and commit. It draws in the corporate design with the colours of bi-designer; the theme of the report still needs bi-designer (above).
3. **No:** a card with three options, recommendation first: (a) the user enables the plugin bi-deneb (VS Code: Customizations › Browse, or the Extensions view under Agent Plugins; Claude Code: `/plugin install bi-deneb@ppp`; then a new session), (b) the nearest standard visual, with what it does not show, (c) a specification written by hand after [visuals.md](visuals.md), without generator, local checks and brand rules. Do not call `bideneb` while its skill is not in your list.
4. Deneb is a certified AppSource visual; whether the tenant allows it is asked once and noted in the README [O per tenant].

The visual counts as done when the user has opened it in Desktop; the local render of bi-deneb proves the picture, not the data.
