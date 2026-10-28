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
- whether a GitHub repository exists, or whether you create one with `gh repo create` (private) after confirmation.

Done when every fact has an answer and the mode is confirmed.

## 2. Create the structure
1. `ppp init --name "<name>" --prefix <PREFIX> --modules <list> --mode <mode> --language <code>` in the project folder. Existing files stay untouched.
2. Material the user hands over goes unchanged to `inputs/` (transcripts, SOPs, mails, presentations with their slide description `<name>.md`, data files).
3. Write the purpose into `README.md` and the five lines into `AGENTS.md`.
4. Set the remote, commit "Intake" and push.

Done when `ppp check` reports no deviation.

## 3. Existing solution (only this branch)
1. Ask for a fresh solution export (tenant-step card: Solutions › the solution › Export › Unmanaged; file into `exchange/`). `ppp unpack exchange/<file>.zip` unpacks, registers the solution and commits it.
2. `ppp inventory` gives every flow compactly; read only the line ranges you need. Fill the inventory READMEs in `components/` and one `components/power-automate/<flow>.md` per flow (purpose, inputs and outputs, sequence, error handling).
3. An app inside the solution: its screens come into `components/power-apps/screens/` only when they are rebuilt; note the app in the inventory now.
4. Derive first drafts of `specs/` from export and material. Mark everything you inferred as an assumption in `STATE.md` under "Open questions and assumptions to confirm".

Done when every component of the export appears in an inventory README and every inferred statement is either confirmed or listed as an assumption.

## 4. Hand over to clarification
Overwrite `STATE.md`: mode, next step "clarification (ppp-clarify)", open questions. Commit and push. Continue with ppp-clarify in the same chat.
