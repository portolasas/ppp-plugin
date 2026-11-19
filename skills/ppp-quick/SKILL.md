---
name: ppp-quick
description: Quick mode - one change to an existing flow, app, report or solution without the project structure, in a quick folder with CHANGE.md. Use when the user wants to change Power Platform material that exists and the folder has no project.json, when project.json has mode quick, and at the end of a quick change (one-off, GitHub, take up as a project).
---

# Quick mode

One change to something that exists: a flow, a screen, a report. The method of ppp holds (proposal, edge cases, checks, cards, tests); the project structure does not. A quick folder holds `project.json` (mode quick), `CHANGE.md`, `.gitignore`, `.gitattributes`, the material and git without a remote. `CHANGE.md` is the only document: it replaces `STATE.md`, `ROADMAP.md`, `proposal.md` and `tasks.md`. Commit locally after each step that changed files, never push (until "Store in GitHub", step 7). The pause card after hours or days holds as everywhere.

In a quick folder start at the step `CHANGE.md` names: no request yet → step 2; a request without a confirmed proposal → step 3; a confirmed proposal → step 4.

## 1. Entry (no project.json yet)
1. The user names the solution: `ppp projects --solution <name>` first. A project of any mode with it comes first on the card: "Continue there (recommended)", "New quick folder". Another working copy of the same solution would have its own base and its own manual notes.
2. One card: **Quick change** (recommended for a single change to something that exists) or **Take up as a project** (skill ppp-intake). When `ppp settings` shows no settings file, ask language and guidance on the same card and save them with `ppp settings`; no publisher in mode quick, it comes from the solution.
3. Ask only what the request lacks. Prefix, modules, storage, language of the handbook and guidance are never asked. The material decides the way:
   - (a) a solution export as ZIP;
   - (b) single parts: screen YAML for "paste code" or a report as PBIP;
   - (c) connected: the user names environment and solution ("fetch it yourself"). Display name of the environment, solution, role of the environment (development, test, production) and "in productive use" stand on one card. With role production say at once that ppp only reads there.
   A single flow JSON has no way into the tenant: ask for (a) or (c).
4. `ppp init --mode quick --solution "<name>"`, connected with `--environment "<display name>" --role <role>`, for (b) with `--modules power-apps` or `power-bi`. A display name of the solution is fine: `ppp connect` turns it into the unique name. Without a folder argument init works in the opened folder when it is a quick folder (empty or only the material, outside sync folders, in no git repository, not the home folder or Documents), else it creates `<quickHome>/<solution>`; it moves the material to its place and derives a provisional prefix. Its output says where it worked.
5. Connected: `ppp connect --in-use yes|no` (with `--project <folder>` for a folder created elsewhere). `AUTH`: a card, the user signs in (`pac auth create`) or the change runs offline (a).
6. Write the request into `CHANGE.md` ("Current change: <title>", "Request" in two sentences) and commit in the quick folder.
7. A folder created elsewhere: a card "open `<folder>` in VS Code and start a new chat there" with the start prompt as a code block above it. This chat goes no further.

Done when the quick folder is committed with `project.json` and the request, and the chat runs in it.

## 2. Starting point
1. The base: connected `ppp export`; with a ZIP `ppp unpack exchange/<file>.zip`; offline without a ZIP a tenant-step card for the export (Solutions › the solution › Export › Unmanaged, file into `exchange/`). Parts (b) are under `components/` already.
2. `ppp inventory`: version, flows, the number of actions and branches per flow. Write it into "Starting point" with the time of the export and what stays untouched (the original, connection references).
3. One card: "Do you see the same in the designer (branches; draft or published)?" An export holds only the published state; a draft in the designer would be lost.

Done when "Starting point" is filled and the user confirmed it.

## 3. Proposal
1. Load the skill of the module. Fill the current change in `CHANGE.md`: request, confirmed edge cases and limits, critical scenarios with values, size before and after (actions and structure; repeat the existing structure for confirmation).
2. A decision card confirms it. A **risky** change (migrates or deletes data, changes permissions or lists, rebuilds a flow in productive use) offers "Audit first" (skill ppp-audit) as the second option.
3. Commit. Then the **one stopping point** of mode quick: `CHANGE.md` stands, so a new chat can continue; card "New chat (recommended)", "Continue here", with the start prompt as a code block above it.

Done when the proposal is confirmed and committed.

## 4. Build and check
- Build with the module skill, as close to the original as possible: change what the request names, keep names, structure and connection references. Keep to the size of the proposal; a build that grows clearly beyond it stops for a card.
- Flows in `solution/<UniqueName>/Workflows/`, screens in `components/power-apps/screens/`, a report in `components/power-bi/`.
- `ppp verify` for a solution, `ppp canvas` for screens (in mode quick it takes the data sources from the screens), `ppp pbi check` for a report, and the tests the change needs.

Done when the checks end with OK or OK WITH WARNINGS and you can give the reason for each warning; commit.

## 5. Pack, import, state after the import
1. A solution: `ppp pack --version <next>`, then the import as in ppp-package step 6: offline a tenant-step card, connected `ppp import` (read [../ppp-package/references/connected.md](../ppp-package/references/connected.md) before the first one) and afterwards `ppp export`. Screens: one card with "paste code" per screen, App Checker, save, publish. A report: publish from Power BI Desktop.
2. Report the switch state of the flows and any warnings; write "Versions and import status" and "State after the import" into `CHANGE.md`. Commit.

## 6. Test
One test card per critical scenario: what exactly to do, the expected values, answers "All as expected", "Deviation – I describe it", "Not possible". Connected: after a scenario that ran a flow, read `ppp runs <flow>` first. A deviation goes to ppp-diagnose or into a fix of this change. Write "Tested and not tested" into `CHANGE.md`; commit.

## 7. End
When the change is tested, or the user stops it, one card: **Leave as a one-off**, **Store in GitHub** or **Take up as a project**. Mode quick ends without `ppp archive` and `ppp tidy`.
- **One-off**: the folder stays local with its history; nothing else.
- **GitHub**: a private repository. The card says that `solution/` may hold company data and personal data. After the yes: `gh repo create <name> --private` (no `--source`, no push), then `ppp storage github --remote <url>`: it checks the whole history for credentials. A `WARNING possible credentials` goes on a card with its places; push only when each is removed from the history or the user calls it harmless. Then `git push -u origin main` after the card; from now on push after each step, also for later changes.
- **Project**: the fact card of ppp-intake step 1, filled with what you know (name, prefix by its rules, modules, storage, language, mode small or medium). Then `ppp init --from-quick --name "<name>" --prefix <PREFIX> --modules <list> --storage <github|local> --mode <small|medium> --language <code>`: each change of `CHANGE.md` becomes an archived package with a `ROADMAP.md` row, manual changes and open points go to `STATE.md`. Commit, then ppp-intake step 3 and ppp-clarify.

## Later changes in the same folder
Recommend **Take up as a project** (card) when a second change comes to a folder with a completed one, when new building blocks such as lists or an app join, or when test persons use the state for their work. If the user stays in mode quick: condense the current change into "Completed changes" as `### <date> <title>` with request, version and result, then start a new current change with the headings of the template. Manual changes in the tenant and open points stay at the top; `ppp check` warns when `CHANGE.md` grows past its budget.
