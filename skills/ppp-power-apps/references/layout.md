# Layout and classic controls

## Size and auto layout
- `Scale to fit = Off`, widths from `Parent.Width`, content in auto-layout containers. Design for at least **1024 × 600** (laptop browser with toolbars); inputs need together at least 4 px air above and below in their row; keep 20 px free on the right for scroll bars in galleries and scrolling containers [B] (PAPPS-20260930-MAC-06).
- Every child of an auto-layout container without X/Y gets `FillPortions` explicitly: `0` together with `Height` (vertical container) or `Width` (horizontal) for a fixed size, `≥ 1` for filling parts. Without it, children fill proportionally and `Height`/`Width` have no effect [B] (PAPPS-20261009-MAC-01). Children also get `LayoutMinWidth` and `LayoutMinHeight` 0; otherwise Studio adds its own minimum sizes on paste and controls stick out of their row [B] (PAPPS-20260929-MAC-01). `bausteine.box` sets all three by default.
- Chips in auto-layout rows: `LayoutMinHeight = 0`, `LayoutMinWidth = 0`, `AlignInContainer.Center`; without them Studio set `LayoutMinHeight = 100` and `Stretch`, and the chip reached into the next row [B] (PAPPS-20260929-MAC-01). In a row made only of borderless labels the chips fill the row height with `PaddingTop`/`PaddingBottom` 0 on the row, `AlignInContainer.Stretch` on the labels and an explicit row height; rows with buttons keep their 2 px padding [B] (PAPPS-20261021-MAC-01).
- Containers from "paste code" get rounding and a border unless given: set the four radii and `BorderThickness` to 0, otherwise flush buttons at the edge are cut [B] (PAPPS-20260930-MAC-04).
- `LayoutWrap` on a horizontal container with vertical child containers made the bar invisible after pasting; build filter bars without `LayoutWrap` (fields with `FillPortions` and `LayoutMinWidth`), `LayoutWrap` only with simple controls as children [O] (PAPPS-20261007-MAC-01).
- Buttons of the same height in an auto-layout row lose a border edge; give the row 2 px padding and 4 px more height. [B]
- Labels with a fixed width wrap long text; size them for the longest display text or allow `AutoHeight`. Icons 24–32 px, rather larger, so they are recognised at a glance.

## Selection controls
- **Multi-select from a collection as a checkbox list** (gallery over the collection, a check per row, selection in a collection), not a combo box: on paste Studio switched `DisplayFields` of a `Classic/ComboBox@2.4.0` with a collection as Items to the first text column and the selection stayed empty, also after a first fix [B][V] (PAPPS-20260930-MAC-01). Person search as text field plus "search" plus hit list. If a combo box is unavoidable: display field as first and alphabetically first text column, and a card after every paste to check `DisplayFields`.
- **Classic dropdowns, combo boxes, date pickers and check boxes** bring their own blue tones [B]; always set (where they exist) `ChevronBackground`, `ChevronFill`, `ChevronHoverBackground`, `ChevronHoverFill`, `SelectionFill`, `SelectionColor`, `PressedFill`, `PressedColor`, `HoverFill`, `HoverColor`, `HoverBorderColor`, `IconBackground`, `IconFill`, `CheckboxBorderColor`, `CheckmarkFill` to theme roles.
- The opened calendar of `Classic/DatePicker@2.6.0` has no colour properties (`CalendarHeaderFill`, `SelectedDateFill`, `HoverDateFill` do not exist) and follows the app theme; settle with the user before designing: accept the theme or build the day selection as dropdown or gallery [B] (PAPPS-20260930-MAC-05).

## Theme, fonts, media
- **Theme as named formulas** in App.Formulas: colours, roles (`Page`, `Surface`, `Text`, `PrimaryFill` …) and font sizes defined once; controls refer to roles only, never to hex values. The generator expects the records `BIRole`, `BIColor`, `BIFont`, `BISize`; brand values come from the skill bi-designer. Canvas font sizes are points (21/17/14/11/9 pt ≈ 28/22/18/14/12 px).
- Own font files cannot be loaded in canvas apps; Segoe UI is the replacement [B][V].
- Logos as SVG, icons as small PNGs in `components/power-apps/assets/`; upload only what is used; media names without `-` (`ic_calendar_clock`); every icon button gets an `AccessibleLabel`.
- Modern controls take theme colours differently (e.g. `BasePaletteColor`) [O][V].

## Timelines and Gantt views [B] (PAPPS-20261001-MAC-01)
An SVG image per gallery row (15 rows × 100 segments rendered in under 0.5 s), with transparent classic buttons of the same segment geometry on top as hover and click zones (`Tooltip` for details; one formula for image and zones). An SVG alone gives no hover events in canvas. Before expanding, measure a small probe app with the target quantities; Power BI Gantt visuals depend on the refresh and do not act back into the app.
