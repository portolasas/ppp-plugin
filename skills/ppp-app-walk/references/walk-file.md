# Walk file

The fields and actions of a walk for `ppp walk`. `ppp walk <file> --check` checks a file offline against them.

## Fields
- `title`, `intro`: chapter title and lead-in of a guide.
- `url`: the play URL.
- `ready`: waits for content in `control`, presses `refresh` when it stays empty and stops with an error instead of an empty picture. The first start of a fresh profile showed an empty list [B].
- `viewports`: the first gives the pictures in `out`, further ones land in a subfolder and serve the review. Without `out` pictures go to `exchange/walks/<name>/`, outside git.
- `mask`: a grey box over each named control with personal data; a mask that never matches is an error. Every picture shows the app's frame only: the player around it shows the signed-in user's name and photo, where no mask reaches [B] (PAPPS-20261103-WIN-05).
- `markColor`: the colour of the frames.
- `ignore`: controls whose findings are intended. `"check": false` on a `shot` skips its measurement.
- `testData`: SKILL.md, section 3. `role`: roles.md.

## Actions
One action per step: `click`, `type` with `value`, `wait`, `hover`, `key`, `scroll` with `by`, `shot`, `expect`. `nth` picks a repeated control such as a gallery row; a click without it picks its row by position only.
- `type` fills the control's own input and checks its value; Ctrl+A after a click beside the input had selected the whole page [B] (PAPPS-20261103-WIN-06).
- `scroll` turns the wheel over the centre of the named control, so a gallery under that point scrolls instead of its container [B]. To scroll the container, name a control of it that is visible and outside any gallery, and check in the picture that the intended area moved; the wheel over a control below the visible app moved nothing [B] (PAPPS-20261102-WIN-01, PAPPS-20261105-WIN-01).
- Classic dropdown: keys Home, End and Enter left it unchanged [B]. Move with a counted number of ArrowUp or ArrowDown from the value it shows, then Enter, then `expect` the value; `--check` warns about Home and End (PAPPS-20261102-WIN-02, PAPPS-20261105-WIN-01).
- Classic date picker: it takes no typed date, its input is read-only, `type` stops at once and `--check` names it [B]. Open it with `click`, move with `key` ArrowLeft or ArrowRight from the date it shows, confirm with `key` Enter, then `expect` the date it shows; an empty one stayed empty after Enter alone and showed today after ArrowLeft, ArrowRight, Enter (PAPPS-20261103-WIN-07).
- `hover` right before a `shot` keeps the pointer for a hover state; otherwise the pointer leaves the app before each picture.
- `"writes": true` marks a step that writes (SKILL.md, section 3). `--check` finds `SubmitForm`, `.Run` and `Patch`, `Remove`, `RemoveIf`, `Update`, `UpdateIf` in the `OnSelect` of a clicked control; on a collection the app fills with `Collect` or `ClearCollect` they change only the app and are no write [B] (PAPPS-20261102-WIN-02).

## Pictures
`shot` names the picture, `crop` cuts it to a control. `marks` draws numbered frames as an overlay in the browser, only for the picture; the app stays unchanged.
- In the first viewport a marked control less than 97 % visible stops the walk, so scroll first or split the shot; in further viewports it is a hint.
- When a marked run deviates where an unmarked one does not, run the same steps without marks before changing the app (GEN-20261105-WIN-04).

## Expected values
```json
{"expect": "lblTotal", "equals": "42", "scenario": "Total after saving"},
{"expect": "lblStatus", "contains": "approved", "within": 120},
{"expect": "lblRow", "count": 3},
{"expect": "lblError", "absent": true}
```
Exactly one of `equals`, `contains`, `count` (visible instances) or `absent`. Without `nth` any instance may match. `within` is how many seconds a value may take to arrive (default 30); raise it when a flow delivers the value. A plain `expect` records a miss and the walk goes on; with `"stop": true` the walk ends at the miss.
