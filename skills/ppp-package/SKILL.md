---
name: ppp-package
description: The package cycle from proposal to archive - build flows, screens and lists offline, check, pack, import and test via cards. Use for every change of a solution, new feature or fix alike, and to continue an active package from STATE.md.
metadata:
  origin: "Fission-AI/OpenSpec@9111a76 (proposal, change folder, spec deltas, archive; files instead of the CLI); MIT; adapted, see THIRD_PARTY.md"
---

# Package cycle

One package is one folder `changes/NNN-name/` and one import. Eight steps; the user confirms the proposal, creates scaffolds, imports and tests the critical scenarios no walk covers, you do everything else. `tasks.md` carries the progress: tick each task when it is done; a note under it only for a deviation or a decision, in one line. Commit and push after each step that changed files, as the core rules say. Facts about export, package and import: [references/solutions.md](references/solutions.md).

**Connected project** (`ppp check` names it at the session start): `ppp export` and `ppp import` replace the export in step 2 and the import card in step 6. Read [references/connected.md](references/connected.md) before the first of them: it says what each answer of `ppp import` asks of you. On `DRIFT:`, `FAILED:`, `ERROR:` or a refusal read [references/connected-trouble.md](references/connected-trouble.md): drift, a failed import, pac that does not get through, a restore. A first solution, the transfer solution's members: [references/connected-create.md](references/connected-create.md).

## 1. Proposal
`ppp new package "<name>"` creates `proposal.md` and `tasks.md` under the number of the planned `ROADMAP.md` row with that name, else under the next free number (GEN-20261102-WIN-01, GEN-20261110-MAC-01). Fill in why, what changes, scope (in and out) and the **critical scenarios**: the few scenarios from `specs/` that must work after this import, with expected values. Changes to the specification go into `changes/NNN-name/specs/<capability>.md` (`ppp new spec-delta "NNN: <capability>"`; sections ADDED, MODIFIED, REMOVED). For a larger package add `design.md` (`ppp new design NNN`); it is optional, so list a package folder before reading it. Mark the package active in `ROADMAP.md` and `STATE.md`. Confirm the proposal with a decision card. After the confirmation say in one line that GPT-6.1 Sol with the small context size (272k) is enough for building from here and how to switch in the model picker, because proposal and design often run on Claude Opus 5.5 (model recommendation A-9).

Notes in `STATE.md` under "Manual changes in the tenant" that touch this package's flows are part of the scope: rebuild them exactly from the note.

## 2. Scaffold and transfer solution (only when needed)
What only the designer can create comes from the user: a new flow with its trigger and one action per connector it needs, a new connection reference, an environment variable, an empty app. A tenant-step card lists the exact steps (names with the prefix, trigger type, inputs) and ends with the export: Solutions › main solution › Export › Unmanaged, file into `exchange/`.

**Connected**: `ppp import --create` builds the empty solution with the publisher of `ppp settings` after a card; the user creates nothing in the portal ([references/connected-create.md](references/connected-create.md), "Create a solution"). **Offline**, without a sign-in, and in the default environment when it lacks the publisher: a card creates the solution and names its publisher with the four values of `ppp settings`; the user creates the publisher in the same dialog: Solutions › New solution › Publisher › New publisher, with Display name, Name, Prefix and Choice value prefix exactly as in the settings, never the environment's default publisher (random prefix). Rules and facts: [references/solutions.md](references/solutions.md), "Publisher".

In a project of mode large the package goes through the transfer solution ([references/solutions.md](references/solutions.md)); without one in `project.json` `<prefix>Transfer` is created first (unmanaged, same publisher as the main solution): connected with `ppp import --create --solution <prefix>Transfer --transfer` (after the card and `--confirmed` it enters the solution in `project.json` itself; nothing by hand), offline by a card. Its members are the components of this package: connected, `ppp members <Name> …` adds the missing ones with their connection references and environment variables, no card ([references/connected-create.md](references/connected-create.md), "Members of the transfer solution"); offline the card adds them. The card recommends removing those no planned package changes (members the user keeps go into the package unchanged). Then the export is that of the transfer solution instead of the main solution.

An export the user reports as stored and `exchange/` lacks was pushed from another computer: `git pull`, then look again. Such a project keeps `exchange/` in git ([../ppp-intake/references/storage.md](../ppp-intake/references/storage.md), "ZIPs for another computer").

Then `ppp unpack exchange/<file>.zip` (connected: `ppp export` instead of the user's export and of this command, at the start of every package); it commits "Export <name> <version>" and shows what changed against the last commit. Changes you did not expect are manual changes in the tenant: compare them with the notes in `STATE.md`.

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
Tenant-step card: Solutions › Import solution › the ZIP from `exchange/` › connections as before › Import; expected result: "successfully imported", flows on, and the checks after the import this package needs on the same card (flow checker without errors, connections, switches, prompts open). "All as expected" or "imported successfully" confirms them; no separate check card. Connected: `ppp import` instead of this card, then the card connected.md names for what stays by hand, then `ppp export` (until it ran, `ppp pack` and `ppp import` refuse). Screens: one card for all screens of the package: in order, per screen the file, "paste code" and its expected result, then App Checker, save and publish; a deviation names the screen.

## 7. Test
Where a walk is possible (skill ppp-app-walk): a layout review of the changed screens the user has pasted, including screens that should not have changed (the comparison with the last run shows them), then a walk with the expected values of each critical scenario. Report its result lines. Then one card per critical scenario or part of one the walk does not cover: what to do, the expected values, answers "All as expected", "Deviation – I describe it", "Not possible". A deviation goes to diagnosis (ppp-diagnose) or into a fix in this package.

## 8. Close
Merge the spec changes into `specs/`; when `ppp check` names handbook walks whose screens changed, run them again and rebuild the Word file (ppp-docs). Then `ppp archive NNN` and `ppp tidy`. A package of screens only imported no ZIP: skip `ppp tidy` and say so, never build or name a ZIP for it; the pictures in `exchange/walks/` are the next run's baseline, recommend keeping them (GEN-20261103-WIN-01). `ppp tidy`: the imported package goes to `exchange/archive/`, intermediate packages and older exports are deleted (`--keep` names the imported package when it is not the newest one). For the other files it lists, ask on one card which may go; diagnosis files of this package are the recommendation, they may hold personal data. Set the package to done in `ROADMAP.md`, overwrite `STATE.md` (no active package, next package, last export = this version), remove manual-change notes that this package rebuilt, commit and push as the core rules say. Then the stopping-point card.
