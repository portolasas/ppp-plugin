---
name: ppp-app-walk
description: Walk through a running canvas app in Edge with automated clicks - pictures, layout review of pasted screens, checks of expected values in scenarios, illustrated Word guide of a process. Use when a screen should be checked visually, a critical scenario tested, or a handbook chapter, guide or screenshots of the app are needed.
---

# Walk through a running app

A **walk** is a JSON file the tool plays in the user's installed Edge, signed in with the user's account. You run it yourself; import, export and "paste code" stay with the user. Status: **[B]** observed in the tenant, **[O]** open; the first walks with clicks settle the [O] points: on a surprise write a lesson.

## 1. Prepare
- Packages once per computer, after a card: `<python> -m pip install --user playwright` for walks, `python-docx` for guides. No browser download; no virtual environment. `ppp walk` names the exact command when one is missing.
- The app is published, the screens are pasted. Ask for the play URL once and keep it in the walk file.
- A visible Edge window opens on the user's computer. Sign-in runs by single sign-on in its own profile `~/.ppp/edge-profile` [B]; if a sign-in page stays open, the user signs in there.

## 2. Write the walk
Location: `tests/walks/<name>.json` for a review, `docs/handbook/walks/<name>.json` for a guide. Control names come from `components/power-apps/screens/`; `report.json` of a run lists the visible ones per picture.

```json
{
  "title": "Create a request", "intro": "For shift leads.",
  "url": "<play URL>",
  "ready": {"control": "galList", "refresh": "btnRefresh"},
  "viewports": [[1366, 800], [1024, 600]],
  "mask": ["lblUserName", "imgUserPhoto"],
  "out": "docs/handbook/images/create-request",
  "steps": [
    {"shot": "start", "marks": [{"control": "btnNew", "label": "New request"}], "text": "Click **New request**.", "caption": "Start screen"},
    {"click": "btnNew"},
    {"type": "txtTitle", "value": "PPP-TEST Request 1", "text": "Enter a title."},
    {"click": "btnSave", "writes": true},
    {"wait": "lblConfirmation"},
    {"shot": "saved", "crop": "conResult"}
  ]
}
```
- One action per step: `click`, `type` with `value`, `wait`, `hover`, `key`, `scroll` with `by`, `shot`, `expect`. `nth` picks a repeated control such as a gallery row.
- `ready` waits for content, presses `refresh` when it stays empty and stops with an error instead of an empty picture. The first start of a fresh profile showed an empty list [B].
- The first viewport gives the pictures in `out`, further ones land in a subfolder and serve the review. Include 1024 x 600, the minimum size in ppp-power-apps. Without `out` pictures go to `exchange/walks/<name>/`, outside git.
- `mask` covers controls with personal data with a grey box; a mask that never matches is an error. Pictures of a guide go into git, so cover every name and photo that the guide does not need.
- `marks` draws numbered frames as an overlay in the browser, only for the picture; the app stays unchanged. `markColor` sets their colour. `text`, `caption` and `label` go into the guide, in `handbookLanguage`.
- `ignore` lists controls whose findings are intended. `"check": false` skips the measurement for a picture.

- `expect` checks what a control shows, see section 5.

`ppp walk <file> --check` checks the file offline. Done when it ends with RESULT: OK.

## 3. Test data
A step that creates, changes or deletes data, sends mail or starts a flow carries `"writes": true`. `--check` finds `Patch`, `SubmitForm`, `Remove`, `Update` and `.Run` directly in the `OnSelect` of a clicked control; read the formula for everything else, named formulas included.

A writing walk is allowed in every environment, under three conditions: the data is clearly identifiable as test data, it can be removed again, and it arises at a time that endangers no production. So:
1. Add `"testData": {"mark": "PPP-TEST", "cleanup": "<how it is removed>"}`; typed values carry the mark.
2. Decision card before the run: what is created, when, which flows and mails it triggers and who receives them, how it is removed.
3. After the confirmation run with `--allow-writes`. It runs once, in the first viewport.
4. Removal is part of the walk's work: a tenant-step card with `cleanup`, or a second walk under the same rules. Done when no data with the mark remains.

## 4. Run and review
`ppp walk <file>`. Report the result lines; console errors and failed requests are among them.

The measured findings are hints: L1 outside the window, L2 outside the parent, L3 cut-off text, L4 overlap, L5 image not loading. Then look at every picture of every viewport yourself with the image tool (`view` in VS Code, `Read` in Claude Code) against `specs/` and ppp-power-apps: alignment, spacing, cut-off and wrapped text, empty areas, colours, scroll bars, whether the state is what the step should show.

Fix in the screen YAML in the current package, or in a new one; the user pastes it by card, and the walk runs again. What you cannot decide alone goes on a decision card with the picture path. Done when every picture was looked at and every finding is fixed, or intended and in `ignore`.

## 5. Scenarios
A critical scenario becomes a walk in `tests/walks/`: the user's steps, then the expected values from the proposal.
```json
{"expect": "lblTotal", "equals": "42", "scenario": "Total after saving"},
{"expect": "lblStatus", "contains": "approved", "within": 120},
{"expect": "lblRow", "count": 3},
{"expect": "lblError", "absent": true}
```
Exactly one of `equals`, `contains`, `count` (visible instances) or `absent`. Without `nth` any instance may match. `within` is how many seconds a value may take to arrive (default 30); raise it when a flow delivers the value. A miss goes into the report as an error with a picture `deviation-<step>.png`, the walk continues, and the run ends with RESULT: ERROR. A scenario that writes follows section 3.

A deviation goes to diagnosis (ppp-diagnose) or into a fix, as after a test card. A scenario counts as tested by the walk only as far as the app shows it. Whatever it does not show stays on a test card for the user: a mail received, a Teams message, a value only in a list, another role, whether the process fits.

## 6. Guide
`ppp guide <walk> [<walk> ...] --title "<title>"` writes `docs/handbook/<first walk>.docx`, one chapter per walk: numbered `text`, pictures with caption, the legend of the frames. `--out` sets the file, `--template` a Word template whose styles apply; if bi-designer is installed, take the template it names, else the neutral look stays. The rules for the chapters are in ppp-docs. The user reviews the Word file.

## State of the evidence
| Statement | Status |
|---|---|
| Edge through Playwright without a browser download, single sign-on in the own profile, conditional access does not block | [B] |
| 80 controls of an app found through `data-control-name`; console and HTTP errors recorded | [B] |
| Clicks, typing, frames and masks at the measured position of a control | [O] tested only on a stand-in with frames |
| `expect` on real canvas markup: text and field values as the runtime renders them | [O] tested only on a stand-in |
| Findings L1–L5 on real canvas markup, especially L3, L4 and the wait for a gallery | [O] tune with `ignore` or a lesson |
