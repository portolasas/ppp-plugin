# YAML for "paste code" (source code schema)

## Skeleton [B] (PAPPS-20260926-MAC-01)
```yaml
Screens:
  scrExample:
    Properties:
      Fill: =BIRole.Page
      OnVisible: |-
        =If(!varBootstrapDone, Set(varBootstrapDone, true); /* bootstrap */)
    Children:
      - conMain:
          Control: GroupContainer@1.5.0
          Variant: AutoLayout
          Properties:
            LayoutDirection: =LayoutDirection.Vertical
            Width: =Parent.Width
            Height: =Parent.Height
          Children:
            - lblTitle:
                Control: Label@2.5.1
                Properties:
                  Text: ="Title"
                  Color: =BIRole.Text
```
- Paste: tree view › right-click on the app or screen level › "paste code". [B]
- Every value starts with `=`. A block scalar `|-` is needed when the value contains a line break, `: ` or ` #`, or starts with `{ [ ' " * & ! % @` or a backtick. Two spaces per level.
- Names with a type prefix: `scr`, `con`, `lbl`, `btn`, `gal`, `img`, `ico`, `txt`, `cmb`, `dp`, `chk`.
- Auto layout: `GroupContainer@1.5.0` with `Variant: AutoLayout`, **without** `LayoutMode` (PA2108). [B]
- Classic and modern (Fluent) controls are not mixed on one screen.

## Control versions [B][V]
Probe September/October 2026, classic controls; the table lives in `plugin/tools/blocks/versionen.py`, a project may keep its own next to its generator:

| Control | Version |
|---|---|
| Label | `Label@2.5.1` |
| Button | `Classic/Button@2.2.0` |
| Rectangle | `Rectangle@2.3.0` |
| Image | `Image@2.2.3` |
| Container | `GroupContainer@1.5.0` (`Variant: AutoLayout` or `ManualLayout`) |
| Gallery | `Gallery@2.15.0`, `Variant: Vertical` |
| Text input | `Classic/TextInput@2.3.2` |
| Dropdown | `Classic/DropDown@2.3.1` |
| Combo box | `Classic/ComboBox@2.4.0` |
| Date picker | `Classic/DatePicker@2.6.0` |
| Check box | `Classic/CheckBox@2.1.0` |
| Timer | `Timer@2.1.0` |

Paste messages: **PA2105** outdated control version, **PA2108** unknown property. Then the user copies one control of that type in Studio ("copy code"), and the version table is updated; never guess. [B]

## Generators
For more than one screen a generator in `components/power-apps/generator/` writes the YAML into `screens/` and App.Formulas into `theme/`; it runs with `ppp run`, which makes the central blocks importable [B]:
- `bausteine`: one function per control (`label`, `knopf`, `box`, `frei`, `galerie`, `auswahl`, `eingabe`, `kombi`, `datum`, `uhr`, `chip`, `rect`, `bild`) and `screen_yaml()`; containers get radius and border 0, auto-layout children minimum sizes 0 and `FillPortions` 0 unless given;
- `pfx.nach_de` for App.Formulas in de-DE, `pfx.pruefe_klammern`;
- `versionen.VERSIONEN`.

Write formulas once in en-US. Every adjustable value is a named constant. For a change run the generator again instead of patching the YAML; unchanged outputs stay byte-identical, so a report of the changed files is enough to read. One screen per file, small enough to paste.

## `ppp canvas` before pasting
Checks every `*.pa.yaml`: values start with `=`, brackets and strings balanced, no `;;` (en-US), no `LayoutMode`, control versions in the table, containers with radius and border, `LayoutWrap` with vertical child containers, `Coalesce(x, "") = ""`, `IfError(<… .Run( …>, Blank())`, and with the data sources `<prefix>_*` (`--sources` names lists without the prefix; a warning says when no filter read one): `Filter(<source>, … IsBlank(x) || …)`, `Filter(<source>, … .Value <> …)` and `ClearCollect(…, <source>)` after `.Run(` without `Refresh(`. `SearchItems` on a combo box is an error: it is not part of the Source Code schema, the paste fails with PA2108 "Unknown property", Studio sets it itself [B] (PAPPS-20261024-WIN-01). Combo boxes are listed as a note.
