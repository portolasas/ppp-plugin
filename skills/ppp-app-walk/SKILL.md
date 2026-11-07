---
name: ppp-app-walk
description: Walk through a running canvas app or click mock-up in Edge with automated clicks - pictures, layout and usability review, expected values in scenarios, reproducing errors, load times, comparison with the last run, illustrated Word guides per role, training videos. Use when a screen should be checked visually, a critical scenario tested, an app error reproduced, or a guide, screenshots or a video of the app are needed.
---

# Walk through a running app

A **walk** is a JSON file the tool plays in the user's installed Edge, signed in with the user's account; a click mock-up works too (ppp-prototype). You run it yourself; import, export and "paste code" stay with the user. Every run on the app goes through `ppp walk`: when it lacks an action, a measurement or an output the task needs, propose a lesson that names the gap and ask on a decision card before writing a project script for it.

Read a reference when its step comes up:
- [references/walk-file.md](references/walk-file.md): every field and action of a walk, and the controls that need their own handling. Before writing or changing a walk.
- [references/review.md](references/review.md): the measured findings, the comparison with the last run and the load times. Before reviewing a run.
- [references/roles.md](references/roles.md): walks in the session of a role. Before a walk for a guide or a test of permissions.
- [references/evidence.md](references/evidence.md): what `ppp walk` handles by itself and why, and what is observed in the tenant **[B]** or still open **[O]**. On a surprise, before writing a lesson; the first walks with clicks settle the [O] points.

## 1. Prepare
- Packages once per computer, after a card: `<python> -m pip install --user playwright` for walks, `python-docx` for guides. No browser download; no virtual environment. `ppp walk` names the exact command when one is missing.
- The app is published, the screens are pasted. Ask for the play URL once and keep it in the walk file.
- `ppp walk` opens a visible Edge window at once, signed in by single sign-on in its own profile `~/.ppp/edge-profile` [B], and waits for `ready` like any step (`--timeout`, 90 s); the app usually loads within a minute (user, 2026-11-04). Run it in the background and read its lines: window open, app ready, each step. On a sign-in page it says so and waits up to ten minutes (`--signin`): a tenant-step card has the user sign in in that window, and the walk goes on by itself.
- After a publication the player can show a bar to update or to confirm connections [B] (PAPPS-20261103-WIN-04): the walk stops at the start with `failed.png`, a tenant-step card has the user confirm the bar in the walk's window, then run again. Make the first step an `expect` with `"stop": true` on a control or text only the new build shows, so a run on the old build stops instead of measuring it.

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
- One action per step. Dropdowns, date pickers, scrolling and frames need their own handling: walk-file.md.
- A review includes 1024 x 600, the minimum size in ppp-power-apps; a guide's walk has one viewport, the screen size of its readers.
- `mask` covers controls with personal data. Pictures of a guide go into git, so cover every name and photo that the guide does not need.

`ppp walk <file> --check` checks the file offline. Done when it ends with RESULT: OK.

## 3. Test data
A step that creates, changes or deletes data, sends mail or starts a flow carries `"writes": true`. `--check` finds the usual writing functions in the `OnSelect` of a clicked control (walk-file.md); read the formula for everything else, named formulas and `Select()` of another control included. A writing click on a repeated control (`nth`) needs right before it an `expect` with `"stop": true` and the same `nth` on the row's test mark, which ends the walk before the click on any other row; `--check` makes it an error (PAPPS-20261105-WIN-03).

A writing walk is allowed in every environment, under three conditions: the data is clearly identifiable as test data, it can be removed again, and it arises at a time that endangers no production. So:
1. Add `"testData": {"mark": "PPP-TEST", "cleanup": "<how it is removed>"}`; typed values carry the mark.
2. Decision card before the run: what is created, when, which flows and mails it triggers and who receives them, how it is removed.
3. After the confirmation run with `--allow-writes`. It runs once, in the first viewport.
4. Removal is part of the walk's work: a tenant-step card with `cleanup`, or a second walk under the same rules. Done when no data with the mark remains.

Test data for a guide stays close to the real thing: use the master data that exists (equipment, steps, groups) unchanged, and create stand-ins only for what a chapter shows being created, modelled on real records. Create and remove what the example needs yourself with writing walks under these rules; a card asks the user only for what no walk can do, such as changing their own role (user, 2026-11-03).

## 4. Run and review
`ppp walk <file>`. Report the result lines; console errors and failed requests are among them. The measured findings are hints; what they mean, the comparison with the last run and the load times: review.md.

Right after the run look at its overviews with the image tool (`view` in VS Code, `Read` in Claude Code): the result lines name each one, up to six pictures side by side in `exchange/walks/<name>/sheets/`. Check them against `specs/` and ppp-power-apps: alignment, spacing, cut-off and wrapped text, empty areas, colours, scroll bars, whether the state is what the step should show. Read the values as well as the layout: a unit without its number, a magnitude no process gives (hundreds of hours lost on one step) or figures that contradict each other are findings for the same decision card; when `specs/` computes them that way, they go to ppp-clarify.
- A step that lands on an empty state keeps its picture as a state of the review; add a populated one beside it.
- In a layout review open every dropdown, combo box and date picker with a `click` and take a `shot`, so the open list is measured and seen too.
- Open a single picture only where a finding, a diff or an overview calls for it. Each image you look at stays in the chat, and beyond 50 every new one has the whole chat processed again at full price.

Fix in the screen YAML in the current package, or in a new one; the user pastes it by card, and the walks of the changed screens run again, not the whole review. Findings left after that go on a decision card before another round, each with its picture and the screens a fix would mean pasting again: fix them in another round, or accept them as intended (user, 2026-11-03). What you cannot decide alone goes on a decision card with the picture path. Done when every overview was looked at and every finding is fixed, or intended and in `ignore`. A review that leaves findings unfixed ends with a decision card: fix them in a package (recommended), diagnose first, or accept them as intended.

## 5. Scenarios
A critical scenario becomes a walk in `tests/walks/`: the user's steps, then `expect` steps with the expected values from the proposal (walk-file.md). A miss goes into the report as an error with a picture `deviation-<step>.png`, the walk continues, and the run ends with RESULT: ERROR; with `"stop": true` the walk ends at the miss. A scenario that writes follows section 3.

A deviation goes to diagnosis (ppp-diagnose) or into a fix, as after a test card; its picture and a `failed.png` lie in `exchange/walks/<name>/`, outside git. A scenario counts as tested by the walk only as far as the app shows it. Whatever it does not show stays on a test card for the user: a mail received, a Teams message, a value only in a list, another role, whether the process fits.

## 6. Guide
A handbook takes its steps and pictures from walks in `docs/handbook/walks/`, one per chapter and role, each run in that role's session (roles.md). `text`, `caption` and `label` of a walk go into the guide, in `handbookLanguage`. `ppp guide` builds the Word files and training decks from the handbook's Markdown and these walks: the rules for the chapters are in ppp-docs, its commands and markers in [ppp-docs/references/guide.md](../ppp-docs/references/guide.md).

## 7. Reproduce an error
`ppp walk <file> --diagnose` plays the user's steps and writes every error of the app per step to `exchange/walks/<name>/diagnosis.json`: console errors, script errors and failed requests with the first 2000 characters of the response; the result lines show the first ten. That is the error text the app does not show. The file may hold personal data and stays outside git. A walk that reproduces the symptom is a feedback loop for ppp-diagnose; with an `expect` on the wrong value it goes red. Steps that write follow section 3.

## 8. Training video
`ppp walk <file> --video` records the walk to `exchange/walks/<name>/video/<name>.webm` instead of taking pictures: each `text` as a caption with time to read, a ring where a click lands, a pause on the `marks` of a `shot`, masks in every frame. One recording in the first viewport; the pictures of the walk stay as they are. Section 3 and roles.md apply. It needs ffmpeg once per computer, after a card: `<python> -m playwright install ffmpeg`; this is a download from Microsoft that company rules may block. Edge plays the file; move a good recording to `docs/training/` on the user's word.
