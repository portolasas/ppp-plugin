---
name: ppp-package
description: The package cycle from proposal to archive - build flows, screens and lists offline, check, pack, import and test via cards. Use for every change of a solution, new feature or fix alike, and to continue an active package from STATE.md.
metadata:
  origin: "Fission-AI/OpenSpec@9111a76 (proposal, change folder, spec deltas, archive; files instead of the CLI); MIT; adapted, see THIRD_PARTY.md"
---

# Package cycle

One package is one folder `changes/NNN-name/` and one import. Eight steps; the user confirms the proposal, creates scaffolds, imports and tests the critical scenarios, you do everything else. `tasks.md` carries the progress: tick each task when it is done; a note under it only for a deviation or a decision, in one line. Commit and push after each step that changed files. Facts about export, package and import: [references/solutions.md](references/solutions.md).

## 1. Proposal
`ppp new package "<name>"` creates `proposal.md` and `tasks.md`. Fill in why, what changes, scope (in and out) and the **critical scenarios**: the few scenarios from `specs/` that must work after this import, with expected values. Changes to the specification go into `changes/NNN-name/specs/<capability>.md` (`ppp new spec-delta "NNN: <capability>"`; sections ADDED, MODIFIED, REMOVED). For a larger package add `design.md` (`ppp new design NNN`). Mark the package active in `ROADMAP.md` and `STATE.md`. Confirm the proposal with a decision card.

Notes in `STATE.md` under "Manual changes in the tenant" that touch this package's flows are part of the scope: rebuild them exactly from the note.

## 2. Scaffold and transfer solution (only when needed)
What only the designer can create comes from the user: a new flow with its trigger and one action per connector it needs, a new connection reference, an environment variable, an empty app. A tenant-step card lists the exact steps (names with the prefix, trigger type, inputs) and ends with the export: Solutions › main solution › Export › Unmanaged, file into `exchange/`.

In a project of mode large the package goes through the transfer solution ([references/solutions.md](references/solutions.md)); without one in `project.json` the card first creates `<prefix>Transfer` (unmanaged, publisher of the main solution). Its members are the components of this package: the card adds the missing ones with their connection references and environment variables, removes those no planned package changes, and exports the transfer solution instead of the main solution.

Then `ppp unpack exchange/<file>.zip`; it commits "Export <name> <version>" and shows what changed against the last commit. Changes you did not expect are manual changes in the tenant: compare them with the notes in `STATE.md`.

If `ppp verify` reports C14 (an app in the solution), the first package removes it: card "Solutions › main solution › the app › Remove from this solution (not delete)", fresh export, `ppp unpack`. Its test checks that the app still calls its flows.

## 3. Build
- **Flows**: edit the workflow JSON in `solution/<UniqueName>/Workflows/`. `ppp inventory <flow>` first, then read only the line ranges you change. Connector actions come only from actions the designer saved (in the scaffold or another flow), never invented. For larger flows a generator in `components/power-automate/generator/` writes the JSON (`ppp run <script>`); keep its output byte-stable.
- **Lists**: change `components/sharepoint/schema.json`, check with `ppp schema`, then `ppp setupflow` writes the setup flow; lists change only through a run of it.
- **Screens**: YAML in `components/power-apps/screens/` (generator with the central blocks `bausteine`, `pfx`, `versionen` via `ppp run`), App.Formulas in `theme/`. They reach the app by "paste code", not by the package.
- Load the module skill before building in a module. Keep the inventory READMEs and `<flow>.md` in `components/` current as you go.

Done when every build task in `tasks.md` is ticked.

## 4. Check locally
`ppp verify` (C1–C14; with `--retry-none` for the writing actions of a setup flow), `ppp canvas` for screens, the project's tests and simulations with `ppp run tests/…`. Report only the result lines in the chat. A test is worth writing only where it is cheaper than finding the error after the import.

Done when `ppp verify` ends with RESULT: OK or OK WITH WARNINGS and you can give the reason for each warning. That the version is not raised yet (C5) is only a hint here; `ppp pack` raises it.

## 5. Pack
`ppp pack --version <next>`: the next version raises the last part of the version in `Other/Solution.xml` by one. It writes `exchange/<Name>_<version>_IMPORTABLE.zip` and the report next to it. A package is the main solution without apps, in mode large the transfer solution.

## 6. Import
Tenant-step card: Solutions › Import solution › the ZIP from `exchange/` › connections as before › Import; expected result: "successfully imported", flows on, and the checks after the import this package needs on the same card (flow checker without errors, connections, switches, prompts open). "All as expected" or "imported successfully" confirms them; no separate check card. Screens: one card per screen with "paste code" from the file.

## 7. Test
One card per critical scenario: what to do, the expected values, answers "All as expected", "Deviation – I describe it", "Not possible". A deviation goes to diagnosis (ppp-diagnose) or into a fix in this package.

## 8. Close
Merge the spec changes into `specs/`, then `ppp archive NNN` and `ppp tidy`: the imported package goes to `exchange/archive/`, intermediate packages and older exports are deleted (`--keep` names the imported package when it is not the newest one). For the other files it lists, ask on one card which may go; diagnosis files of this package are the recommendation, they may hold personal data. Set the package to done in `ROADMAP.md`, overwrite `STATE.md` (no active package, next package, last export = this version), remove manual-change notes that this package rebuilt, commit and push. Then the stopping-point card.
