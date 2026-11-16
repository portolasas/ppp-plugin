# Power Apps (canvas) – applying the brand

Legend: [B] confirmed · [O] open (verify in the tenant) · [V] version-dependent

## 1. Theme as named formulas (App › Formulas) [B]
Paste once into `App.Formulas`; afterwards every control references tokens, never raw hex values.
Values below are for Boehringer Ingelheim (from `marken/boehringer-ingelheim/tokens.json`).
**Notation:** the block below is en-US. The formula bar needs the user's Studio notation – de-DE:
`,` → `;` inside records/arguments and `;` → `;;` after each formula (skill ppp-power-apps). In ppp projects keep
the en-US block in `components/power-apps/theme/` and create the de-DE variant with `ppp formulas`; YAML screens stay en-US.

```
BIColor = {
    DarkGreen: ColorValue("#08312A"), AccentGreen: ColorValue("#00E47C"),
    White: ColorValue("#FFFFFF"), LightGray: ColorValue("#F6F5F3"), WarmGray: ColorValue("#E5E3DE"),
    Black: ColorValue("#000000"),
    LightBlue: ColorValue("#D2F2F7"), DarkBlue: ColorValue("#076D7E"),
    MediumYellow: ColorValue("#FFD03D"), LightYellow: ColorValue("#FBF9AA"),
    LightRed: ColorValue("#F5CDB9"), DarkRed: ColorValue("#86251B"),
    LightViolet: ColorValue("#E0E1F6"), DarkViolet: ColorValue("#5D4495"),
    Gray5: ColorValue("#B7B6B2"), Gray7: ColorValue("#5C5B59"),
    SignalGreen: ColorValue("#1EAD1B"), SignalYellow: ColorValue("#FF8413"), SignalRed: ColorValue("#F62B2B")
};
BIRole = {
    Header: BIColor.DarkGreen, HeaderText: BIColor.White, HeaderAccent: BIColor.AccentGreen,
    Page: BIColor.LightGray, Surface: BIColor.White, Border: BIColor.WarmGray, Text: BIColor.DarkGreen,
    PrimaryFill: BIColor.DarkGreen, PrimaryText: BIColor.White,
    PrimaryPressedFill: BIColor.AccentGreen, PrimaryPressedText: BIColor.DarkGreen,
    FocusLight: BIColor.DarkGreen, FocusDark: BIColor.AccentGreen,
    OkFill: BIColor.AccentGreen, OkText: BIColor.DarkGreen,
    InfoFill: BIColor.LightBlue, InfoText: BIColor.DarkBlue,
    WarnFill: BIColor.MediumYellow, WarnText: BIColor.DarkGreen,
    ErrorFill: BIColor.LightRed, ErrorText: BIColor.DarkRed,
    NeutralFill: BIColor.WarmGray, NeutralText: BIColor.DarkGreen,
    Scrim: ColorValue("#08312A99")
};
BIFont = { Head: Font.'Segoe UI', Text: Font.'Segoe UI' };
BISize = { H1: 21, H2: 17, H3: 14, Body: 11, Small: 9 };
BISpace = { XS: 4, S: 8, M: 16, L: 24, XL: 32 };
```
- Canvas font sizes are points: 21/17/14/11/9 pt ≈ 28/22/18/14/12 px.
- Canvas apps cannot load custom font files → Segoe UI stands in for Boehringer Forward. [B – platform limit, V]
- Named formulas with records work (confirmed 09/2026, de-DE Studio). `Scrim` = Dark Green 60 % for
  overlays (access lock, dialogs).

## 2. Status mapping (example for run/review status)
```
BIStatus(s: Text): Record = Switch(s,
    "Review",  {Fill: BIRole.InfoFill,    Text: BIRole.InfoText},
    "Fehler",  {Fill: BIRole.ErrorFill,   Text: BIRole.ErrorText},
    "Erledigt",{Fill: BIRole.OkFill,      Text: BIRole.OkText},
    "Neu",     {Fill: BIRole.NeutralFill, Text: BIRole.NeutralText},
               {Fill: BIRole.WarnFill,    Text: BIRole.WarnText});
```
User-defined functions were accepted in a tenant (09/2026) [B, V]; two functions returning `Color`
(`BIStatusFill(s)`, `BIStatusText(s)`) keyed by the **technical** value are the proven form. If rejected,
inline the `Switch` in `Fill`/`Color` of the status label. Show Klarnamen via a label lookup, never
the technical value.

## 3. Control recipes (classic controls)
| Control | Properties |
|---|---|
| Screen | `Fill = BIRole.Page` |
| Header container/rectangle (height 56–64) | `Fill = BIRole.Header`; title label `Color = BIRole.HeaderText`, `Font = BIFont.Head`, `FontWeight = FontWeight.Semibold`, `Size = BISize.H2`; logo image right or left (variant Accent Green or White) |
| Card / gallery item | `Fill = BIRole.Surface`, `BorderColor = BIRole.Border`, `BorderThickness = 1`, `RadiusTopLeft…` = 0–4 |
| Primary button | `Fill = BIRole.PrimaryFill`, `Color = BIRole.PrimaryText`, `HoverFill = BIRole.PrimaryFill`, `HoverBorderColor = BIColor.AccentGreen`, `PressedFill = BIRole.PrimaryPressedFill`, `PressedColor = BIRole.PrimaryPressedText`, `FocusedBorderColor = BIRole.FocusLight`, `FocusedBorderThickness = 2` |
| Secondary button | `Fill = BIRole.Surface`, `Color = BIRole.Text`, `BorderColor = BIRole.Text`, `BorderThickness = 1` |
| Text input | `BorderColor = BIRole.Border`, `FocusedBorderColor = BIRole.FocusLight`, `Color = BIRole.Text` |
| Selected gallery item | left bar 4 px `Fill = BIColor.AccentGreen` on Dark Green nav, or `Fill = BIColor.LightGray` + Dark Green text on light lists |
| Status chip | label with `Fill`/`Color` from BIStatus, `Size = BISize.Small`, padding 4/8 |

Classic dropdown, combo box, date picker and check box bring their own blue tones: set all their
color properties to roles (list in ppp-power-apps `references/layout.md`).

Modern controls (Fluent based) take theme colors differently (e.g. `BasePaletteColor`, app theme) [O][V]:
set `BasePaletteColor = BIColor.DarkGreen` where available and verify contrast; do not mix classic and
modern controls on one screen.

## 4. Logo and icons in the app
- Copy only the files you need into the project (`design/assets/`), then **Media › Upload** in Power Apps
  Studio. Naming in the app: `bi_logo_white`, `bi_symbol_darkgreen`, `ic_calendar_darkgreen` …
- SVG for logo/symbol (sharp at every size); icons are PNG 512 px – display 24–32 px, rather larger:
  32 px in list rows, 28 px in messages, 24 px in navigation (user feedback: recognisable at a glance).
- Media names cannot contain `-`: `calendar-clock` → `ic_calendar_clock_darkgreen`.
- Image control: `Image = bi_logo_white`, `ImagePosition = ImagePosition.Fit`, transparent fill.
- Upload only used icons (app size); a SharePoint picture library is the alternative for large sets [O].
- Accessibility: `AccessibleLabel` on every icon button; decorative images `AccessibleLabel = ""`.

## 5. Checks before handing over
- Every color comes from `BIColor`/`BIRole` (no stray hex values).
- Contrast pairs only from the allowed list in MARKE.md; no Accent Green on light backgrounds.
- Logo variant fits the background; no recoloring.
- Longest Klarname fits its label without unwanted wrap; icon sizes as in §4.
