# Hand-over to Power BI Desktop

The local render proves the picture with invented rows. Desktop proves the rest. Give the user this list with the
hand-over, shortened to what applies to the visual; write it as a card in a ppp project.

## Before bideneb writes
The project is closed in Desktop, or the user reopens it afterwards without saving. Desktop holds the report in
memory and writes it over the files when it saves; what bideneb embedded in between is then gone.

## Checks by the user
1. **Open.** Open the project (`.pbip`). Deneb loads from AppSource on first use. The page shows the visual, no
   "Can't display this visual" and no landing page of Deneb. On its first save Desktop adds its own version
   properties to the visual; that changes the file, not the picture.
2. **Values.** Compare two values with a table visual of the same fields and filters: one ordinary, one at the edge
   (largest, an empty one). Numbers carry the format of the measure, decimal comma and thousands point as in the report.
3. **Dates and times.** One known point in time reads as in the model, not shifted by one or two hours.
4. **Tooltip.** Hovering a mark shows the fields with formatted values.
5. **Cross-filter** (if on). A click on a mark filters the other visuals of the page and fades the other marks; a
   click on the empty area clears it; Ctrl+click adds.
6. **Sizes.** Narrow and widen the visual once: nothing is cut off, labels do not overlap.
7. **Slicers.** One slicer change: the visual follows, an empty selection shows an empty visual, not an error.

## What the answers mean
| The user reports | Cause and next step |
|---|---|
| every visual of a copied report is empty, also the standard ones | a PBIP copied without `.pbi/cache.abf` has no rows until a refresh: Home › Refresh, then look again |
| slicers or other visuals were gone after the first save | they belonged to a group that was not on the page (copied from another page): `bideneb check` (R10) |
| the visual is empty after a slicer change or a click, with rows in the table | a signal kept a state from the old rows: `bideneb live` (L1, L3) |
| "Can't display this visual" | Deneb is not in `publicCustomVisuals`, or AppSource visuals are blocked in the tenant: `bideneb check` (R1); otherwise the tenant setting is the user's to clarify |
| Deneb landing page, no chart | no field arrived: the projections do not match the model; `bideneb check` (R5), `bideneb fields` |
| an empty area | a field key or a filter: open the Deneb editor (… › Edit), the log pane names the error; send its text |
| the editor names a field as missing | the display name differs from the key in the brief (renamed in the Values well): set `"as"` in the brief, build, embed |
| numbers in another format than the picture | expected: the local render approximates `pbiFormat`; Desktop is right. A wrong format is changed on the measure |
| times shifted | the model delivers UTC; convert to local time in the model, not in the specification |
| extra fields `…__format`, `…__formatted` in the data pane | the visual was treated as a legacy one: `bideneb check` (R4), `bideneb embed` |
| the click does nothing | interactions of the page are off for this visual, or marks are aggregated: Format › Edit interactions; `bideneb check` (X3) |
| the user changed the specification in the editor | after saving the project: `bideneb pull <name>`, then `bideneb check` |

## Without write access to the report
`bideneb template <name>` writes a Deneb template. The user adds a Deneb visual, puts the fields into Values, opens
the editor, chooses New specification › Import template and assigns each placeholder its field; the command lists
the assignments.

## Where the facts come from
Format of `visual.json`: a file Power BI Desktop saved for Deneb 2.0.1 and the Deneb source (text literals in single
quotes with `'` doubled, booleans bare, numbers with `D`; `stateManagement.denebMetaVersion` `'2'`). Desktop accepted
a hand-written `visual.json` with `jsonSpec` and rewrote it on save, adding `vega.version`, `developer.version` and
its own state: `bideneb embed` keeps those on an update.
