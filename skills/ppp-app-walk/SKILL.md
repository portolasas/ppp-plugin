---
name: ppp-app-walk
description: Walk through a running canvas app or click mock-up in Edge with automated clicks - pictures, layout and usability review, expected values in scenarios, reproducing errors, load times, comparison with the last run, illustrated Word guides per role, training videos. Use when a screen should be checked visually, a critical scenario tested, an app error reproduced, or a guide, screenshots or a video of the app are needed.
---

# Walk through a running app

A **walk** is a JSON file the tool plays in the user's installed Edge, signed in with the user's account; a click mock-up works too (ppp-prototype). You run it yourself; import, export and "paste code" stay with the user. Status: **[B]** observed in the tenant, **[O]** open; the first walks with clicks settle the [O] points: on a surprise write a lesson.

## 1. Prepare
- Packages once per computer, after a card: `<python> -m pip install --user playwright` for walks, `python-docx` for guides. No browser download; no virtual environment. `ppp walk` names the exact command when one is missing.
- The app is published, the screens are pasted. Ask for the play URL once and keep it in the walk file.
- After a publication the player can show a bar above the app to update or to confirm connections [B] (PAPPS-20261103-WIN-04). Before the run the user confirms it in the walk's Edge window on a tenant-step card; a prompt for other permissions or a sign-in stops the walk. The first step is an `expect` on a control or text only the new build shows, so a run on the old build stops instead of measuring it.
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
- `scroll` turns the wheel over the centre of the named control, so a gallery under that point scrolls instead of its container [B]: to scroll the container, name a control of it outside any gallery and check in the picture that the intended area moved (PAPPS-20261102-WIN-01).
- Keys End and Enter left a classic dropdown unchanged [B]: after choosing a value, `expect` the value it shows (PAPPS-20261102-WIN-02).
- `ready` waits for content, presses `refresh` when it stays empty and stops with an error instead of an empty picture. The first start of a fresh profile showed an empty list [B].
- The first viewport gives the pictures in `out`, further ones land in a subfolder and serve the review. Include 1024 x 600, the minimum size in ppp-power-apps. Without `out` pictures go to `exchange/walks/<name>/`, outside git.
- `mask` covers controls with personal data with a grey box; a mask that never matches is an error. Pictures of a guide go into git, so cover every name and photo that the guide does not need.
- `marks` draws numbered frames as an overlay in the browser, only for the picture; the app stays unchanged. `markColor` sets their colour. `text`, `caption` and `label` go into the guide, in `handbookLanguage`.
- `ignore` lists controls whose findings are intended. `"check": false` skips the measurement for a picture.

- `expect` checks what a control shows, see section 5.

`ppp walk <file> --check` checks the file offline. Done when it ends with RESULT: OK.

## 3. Test data
A step that creates, changes or deletes data, sends mail or starts a flow carries `"writes": true`. `--check` finds `SubmitForm`, `.Run` and `Patch`, `Remove`, `RemoveIf`, `Update`, `UpdateIf` in the `OnSelect` of a clicked control; on a collection the app fills with `Collect` or `ClearCollect` they change only the app and are no write [B] (PAPPS-20261102-WIN-02). Read the formula for everything else, named formulas and `Select()` of another control included.

A writing walk is allowed in every environment, under three conditions: the data is clearly identifiable as test data, it can be removed again, and it arises at a time that endangers no production. So:
1. Add `"testData": {"mark": "PPP-TEST", "cleanup": "<how it is removed>"}`; typed values carry the mark.
2. Decision card before the run: what is created, when, which flows and mails it triggers and who receives them, how it is removed.
3. After the confirmation run with `--allow-writes`. It runs once, in the first viewport.
4. Removal is part of the walk's work: a tenant-step card with `cleanup`, or a second walk under the same rules. Done when no data with the mark remains.

## 4. Run and review
`ppp walk <file>`. Report the result lines; console errors and failed requests are among them.

The measured findings are hints: L1 outside the window, L2 outside the parent, L3 text cut off by its control or by a clipping box inside it, measured on the text's own rectangles, so the chevron of a dropdown and the frame of a combo box count and a small overhang is font metrics (PAPPS-20261103-WIN-02, PAPPS-20261103-WIN-03), L4 overlap, L5 image not loading, L6 a button label on more than one line, L7 a painted border cut by a parent, L8 a word broken over two lines; for usability A1 clickable without text or `AccessibleLabel`, A2 click area under 24 px, A3 text contrast under 4.5:1. Then look at every picture of every viewport yourself with the image tool (`view` in VS Code, `Read` in Claude Code) against `specs/` and ppp-power-apps: alignment, spacing, cut-off and wrapped text, empty areas, colours, scroll bars, whether the state is what the step should show.

In a layout review open every dropdown, combo box and date picker with a `click` and take a `shot`, so the open list is measured and seen too.

From the second complete run on, every picture is compared with the last one; the result lines name each changed picture with its area and a diff in `exchange/walks/<name>/diff/` (changed pixels red). Look at each diff: a change outside the package's scope is a finding. Moving data such as dates also shows up there; cover it with `mask` if it gets in the way.

The run also measures time and requests: from the action to the last visible change, for the start and each `click`, `type`, `key` and `wait`, all in `report.json`, those from one second on in the result lines. A step clearly slower than in the last complete run is a warning; go through ppp-power-apps (performance) for it. Compare like with like: the first start of a fresh profile is slower, and a second viewport runs in a warm browser.

Fix in the screen YAML in the current package, or in a new one; the user pastes it by card, and the walk runs again. What you cannot decide alone goes on a decision card with the picture path. Done when every picture was looked at and every finding is fixed, or intended and in `ignore`. A review that leaves findings unfixed ends with a decision card: fix them in a package (recommended), diagnose first, or accept them as intended.

## 5. Scenarios
A critical scenario becomes a walk in `tests/walks/`: the user's steps, then the expected values from the proposal.
```json
{"expect": "lblTotal", "equals": "42", "scenario": "Total after saving"},
{"expect": "lblStatus", "contains": "approved", "within": 120},
{"expect": "lblRow", "count": 3},
{"expect": "lblError", "absent": true}
```
Exactly one of `equals`, `contains`, `count` (visible instances) or `absent`. Without `nth` any instance may match. `within` is how many seconds a value may take to arrive (default 30); raise it when a flow delivers the value. A miss goes into the report as an error with a picture `deviation-<step>.png`, the walk continues, and the run ends with RESULT: ERROR. A scenario that writes follows section 3.

A deviation goes to diagnosis (ppp-diagnose) or into a fix, as after a test card; its picture and a `failed.png` lie in `exchange/walks/<name>/`, outside git. A scenario counts as tested by the walk only as far as the app shows it. Whatever it does not show stays on a test card for the user: a mail received, a Teams message, a value only in a list, another role, whether the process fits.

## 6. Guide
`ppp guide <walk> [<walk> ...] --title "<title>"` writes `docs/handbook/<first walk>.docx`, one chapter per walk: numbered `text`, pictures with caption, the legend of the frames. `--out` sets the file, `--template` a Word template whose styles apply; if bi-designer is installed, take the template it names, else the neutral look stays. The rules for the chapters are in ppp-docs. The user reviews the Word file.

## 7. Reproduce an error
`ppp walk <file> --diagnose` plays the user's steps and writes every error of the app per step to `exchange/walks/<name>/diagnosis.json`: console errors, script errors and failed requests with the first 2000 characters of the response; the result lines show the first ten. That is the error text the app does not show. The file may hold personal data and stays outside git. A walk that reproduces the symptom is a feedback loop for ppp-diagnose; with an `expect` on the wrong value it goes red. Steps that write follow section 3.

## 8. Roles
A guide shows every action from the session of the role that does it, with that role's permissions, never from a developer account that sees more. So one walk per role and task:
```json
"role": {"name": "Shift lead", "identity": {"control": "lblRole", "equals": "Shift lead"}}
```
- `identity` names a control that shows who is signed in or which role the app assigned, with `equals` or `contains`. The run stops without a picture when it does not match; single sign-on may quietly log in the user's own account. If the app shows no such control, add one to the screens first, in a package.
- Each role has its own browser profile `~/.ppp/edge-profile-<role>`. First run per role with `--timeout 600`: a tenant-step card has the user sign in with the role's test account in the window that opens. Passwords stay with the user.
- Without a test account per role: decision card with what is possible, for example a list entry that assigns the role to the user's own account while the walk runs, with the rules of section 3.
- A click on a control the role lacks stops the run, as does a disabled one. That is the check that the chapter fits the role; a step the role cannot do does not belong in its chapter, or it reveals a defect in the permissions.
- Add `expect` with `absent` for what this role must not see, from `specs/`, so the walk also tests the permissions. A check that runs in a flow shows only by doing the step: follow section 3.
- `ppp guide <walks> --role "<name>"` builds the guide of one role from the given walks, `docs/handbook/<first walk>-<role>.docx`, and names the role under each chapter title. It refuses pictures from a run that did not finish or is not proven as that role.

## 9. Training video
`ppp walk <file> --video` records the walk to `exchange/walks/<name>/video/<name>.webm` instead of taking pictures: each `text` as a caption with time to read, a ring where a click lands, a pause on the `marks` of a `shot`, masks in every frame. One recording in the first viewport; the pictures of the walk stay as they are. The rules of sections 3 and 8 apply. It needs ffmpeg once per computer, after a card: `<python> -m playwright install ffmpeg`; this is a download from Microsoft that company rules may block. Edge plays the file; move a good recording to `docs/training/` on the user's word.

## State of the evidence
| Statement | Status |
|---|---|
| Edge through Playwright without a browser download, single sign-on in the own profile, conditional access does not block | [B] |
| 80 controls of an app found through `data-control-name`; console and HTTP errors recorded | [B] |
| Clicks, typing, frames and masks at the measured position of a control | [O] tested only on a stand-in with frames |
| `expect` on real canvas markup: text and field values as the runtime renders them | [O] tested only on a stand-in |
| `--diagnose`: which errors of connectors the runtime shows as failed requests, and the headers `x-ms-request-url` and `x-ms-request-method` | [O] |
| `--video` on the company computer: ffmpeg download, quality on real apps | [O] |
| A second account in its own profile despite single sign-on on the company computer; how the canvas runtime marks disabled controls | [O] |
| Findings L1–L5 and A1–A3 on real canvas markup, especially L3, L4, the roles behind A1 and the wait for a gallery | [O] tune with `ignore` or a lesson |
| L3 on text rectangles and L8 as measured by `ppp walk`; the cause, a clipping box inside dropdowns and combo boxes, is [B] (PAPPS-20261103-WIN-02, PAPPS-20261103-WIN-03) | [O] |
| L6 and L7 as measured by `ppp walk`; the cause, the border layer `appmagic-borderfill-container` with `margin: -0.5px`, is [B] (PAPPS-20261103-WIN-01) | [O] |
