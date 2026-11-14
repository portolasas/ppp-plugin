---
name: ppp-intake
description: Intake of a project into ppp. Use when a folder has no project.json yet - a new solution, or an existing solution or app built without ppp that should now be maintained with ppp.
---

# Intake

Intake ends with a project in the ppp structure whose `STATE.md` points to clarification. Two branches: a **new** project, or an **existing** solution built without ppp.

Projects with a `.ppp/` folder come from PPP 0.17. They are adopted by the transition procedure of the ppp repository, not by this skill; tell the user and stop.

## 1. Facts of the project
Ask on one round of cards, each with your recommendation:
- name, and purpose in one or two sentences;
- prefix: letters and digits, put before every flow, list and component (`ASUM_Setup`, `ASUM_Rollen`);
- modules: power-automate, power-apps, sharepoint, power-bi, copilot-studio;
- mode: recommend **small** for a few flows or a single screen, **medium** for a typical solution (an app with 5–6 screens and 3–4 flows), **large** when several teams, many lists or a formal concept are involved; the user confirms;
- language of handbook and training (the end users' language);
- storage, where the project data lives: **GitHub** (private repository), **local folder** (git without a remote, no server, backups on request) or **Bitbucket** (in preparation: starts as local folder); recommend the storage of the user's other ppp projects. Each one's way: [references/storage.md](references/storage.md).
- tenant: **connected** to one environment, which `ppp` then exports from and imports into itself, or **offline** (the user exports and imports by hand, guided by cards), the third choice. Offline, ask on the same card whether exports and imports happen on another computer than this one; then `exchange/` travels through git (storage.md, "ZIPs for another computer"). Connected needs pac signed in on this computer; the environment is named by its display name. The default "Citizen Developments" stays the default, since every user has it. Working in an own development environment is the user's free choice (`ppp connect` names the usual times). Recommend what the user's other ppp projects use;
- only when connected: the role of the environment, on the same card (pac does not name it): **development** (built and imported here), **test** (a package moves here for the user test; ppp imports after a card) or **production** (ppp only reads);
- publisher of the solution: show the one from `ppp settings` for confirmation. Without one, ask on the same card: does the user already have a publisher (take it from an existing solution with `ppp settings --publisher-from solution/<Name>`, or name its four values), or is a new one needed (fix the values, then `ppp settings --publisher-name … --publisher-prefix … --publisher-option-prefix …`)? Rules: [../ppp-package/references/solutions.md](../ppp-package/references/solutions.md), "Publisher". With an existing solution it comes from its export (step 3); with a new, connected project `ppp import --create` creates the main solution with it (step 2);
- only when connected: the card before an import, **before every import** (recommended) or **only on a deviation** in the tenant and on the first import of ppp from this project into the environment (role `test`: always a card).

Done when every fact has an answer and the mode is confirmed.

## 2. Create the structure
1. `ppp init --name "<name>" --prefix <PREFIX> --modules <list> --mode <mode> --language <code> --storage <github|local> --publisher <UniqueName>` in the project folder (a new, connected project also names its main solution: `--solution <UniqueName>`, no spaces) (the publisher defaults to the one in the settings); Bitbucket takes `local`. Existing files stay untouched. Connected: add `--environment "<display name>" --role <development|test|production> --confirm-import <yes|no>` (without `--role` init writes none and `ppp connect` demands it), then run `ppp connect`; it finds the environment's address and says which solutions are online. For an existing solution `ppp connect` takes `--in-use yes` when the solution is in productive use there. When `ppp connect` ends with `AUTH`, ask on a card: the user signs in (`pac auth create` in a terminal), or the project starts offline (`ppp connect --off`).
2. New, connected project: `ppp connect` printed a line on the publisher (`MISSING Publisher …` is expected). `ppp import --create` answers `CONFIRM FIRST`: a card with the answers "Create" and "Not now", then the command with the `--confirmed <code>` the line names, then `ppp export --solution <UniqueName>` for the first base. The user creates nothing in the portal; the cases (default environment without the publisher, a differing publisher, offline) are in [../ppp-package/references/connected-create.md](../ppp-package/references/connected-create.md), "Create a solution".
3. Material the user hands over goes unchanged to `inputs/` (transcripts, SOPs, mails, presentations with their slide description `<name>.md`, data files). `inputs/README.md` is its index, `| File | Origin | Note | State |`: one row per file or folder, state `new`. A Power BI report comes as PBIP into `components/power-bi/`, a `.pbix` is saved as PBIP by the user (skill ppp-power-bi).
4. Write the purpose into `README.md` and the five lines into `AGENTS.md`.
5. Save the start as references/storage.md says for the storage: GitHub with remote, commit "Intake" and push; local folder and Bitbucket with commit "Intake" and the backup folder of this computer. When `ppp settings` shows a `teamHome`, ask on a decision card whether the project is shared with the team (storage.md, "Team folder").

Done when `ppp check` reports no deviation.

## 3. Existing solution (only this branch)
1. Ask for a fresh solution export (tenant-step card: Solutions › the solution › Export › Unmanaged; file into `exchange/`). `ppp unpack exchange/<file>.zip` unpacks, registers the solution and commits it. Connected: `ppp export --solution <UniqueName>` does all of this without a card. Without a stored publisher take it from the solution: `ppp settings --publisher-from solution/<Name>`.
2. `ppp inventory` gives every flow compactly; read only the line ranges you need. Fill the inventory READMEs in `components/` and one `components/power-automate/<flow>.md` per flow (purpose, inputs and outputs, sequence, error handling).
3. An app inside the solution: its screens come into `components/power-apps/screens/` only when they are rebuilt; note the app in the inventory now.
4. Derive first drafts of `specs/` from export and material. Mark everything you inferred as an assumption in `STATE.md` under "Open questions and assumptions to confirm".

Done when every component of the export appears in an inventory README and every inferred statement is either confirmed or listed as an assumption.

## 4. Hand over to clarification
Overwrite `STATE.md`: mode, next step "clarification (ppp-clarify)", open questions. Commit and push as the core rules say. Continue with ppp-clarify in the same chat.
