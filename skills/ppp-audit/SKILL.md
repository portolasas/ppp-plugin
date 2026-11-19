---
name: ppp-audit
description: Independent audit of the plan or of a package proposal by a read-only subagent never weaker than the chat's model - contradictions, gaps, unconfirmed assumptions, testability. Use when the user picks "Audit first" on the confirmation card of the plan or of a risky package, or asks for an audit or a second opinion on specs, plan or proposal.
---

# Audit

A second reader checks the work before the user confirms it. The auditor sees only the files, never this chat, and is never weaker than the chat's model; where it can, it runs on the other model family, so it does not share your blind spots. One round per object; a second round only when the user asks for it.

## 1. Collect the files
- **Plan** (ppp-plan): `ROADMAP.md`, every file in `specs/` and `decisions/`, `inputs/README.md`, the section "Open questions and assumptions to confirm" of `STATE.md`.
- **Package** (ppp-package step 1): the folder `changes/NNN-name/`, the files in `specs/` it changes, the notes in `STATE.md` under "Manual changes in the tenant", and the descriptions in `components/` of the flows, lists and screens in its scope.
- **Quick change** (ppp-quick step 3): `CHANGE.md` (its current change and the manual changes in the tenant) and the flows, screens or report the change touches.

Done when every file the object rests on is in the list, as project-relative paths.

## 2. Start the auditor
Say in one line that the audit starts and on which model, given as ID:
- **VS Code**: in a GPT chat `claude-opus-5.5`, in a Claude chat `gpt-6.2-sol`.
- **Claude Code**: only Claude models; always `opus`, also when the chat runs on Opus. Subagent type `Explore` (read-only).

Its task, filled in:

> You audit the <plan | proposal of package NNN | current change in CHANGE.md> of a Power Platform project in mode <mode>. Read only these files, change nothing: <paths>. Goal of the project: <one sentence from README.md>.
> Look for: contradictions between requirements, decisions and the <plan | proposal>; gaps (roles and permissions, error paths, data volume and the list threshold, migration and deletion, personal data, operation after go-live); assumptions nobody confirmed; for a plan, a requirement without a package, a package without a goal testable in a few minutes, an order against the dependencies (lists and setup flow, then writing flows, then app, then reports); for a package, a change in scope without a critical scenario, and behaviour that must keep working without one.
> A confirmed requirement stays as written: report only its contradiction with another one.
> Answer with at most 10 findings, most severe first, each: severity (critical, important, note), file and section, finding in one sentence, proposal in one sentence. "No findings" is a valid answer.

## 3. Weigh the findings
Check each finding against the files yourself. Drop what the files already answer or what disputes a confirmed requirement, with one line of reason each. Then in the chat: the findings you keep, the dropped ones with their reason.
- **critical** and **important**: one decision card each, "Adopt" (recommended when the finding holds), "Reject", "Later"; the card names the change you would make.
- **note**: one line each in the chat, no card.

Done when every kept finding is adopted, rejected or noted for later. Adopted findings change `specs/`, `ROADMAP.md` or the proposal; "Later" goes to `STATE.md` under "Open questions and assumptions to confirm". In mode quick both go to `CHANGE.md`: adopted ones into the current change, "Later" under "Open points". Then back to the confirmation card the audit came from.
