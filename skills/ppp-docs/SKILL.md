---
name: ppp-docs
description: Documents for people outside development - handbook, training, Six Sigma documents, questionnaires and project material in docs/. Use when a handbook, training, user guide, in-app help, DMAIC document or presentation is needed.
---

# Documents for people

The technical documentation is the project structure itself (`README.md`, `specs/`, the READMEs in `components/`, `decisions/`); keep it current per package. This skill covers what end users, trainers and the business read. These documents are in the language of the end users (`handbookLanguage` in `project.json`).

## Handbook (`docs/handbook/`)
1. **Outline with the users**: ask who reads it and for which tasks; one chapter per task, in the order the users work, not per screen; one handbook with a section per role, or one per role, as the users want.
2. **Text in Markdown**: `docs/handbook/<name>.md` holds the whole handbook: version, date and the solution version it describes, a short section "New in this version" with what the last package changed for the users, start, terms, and per task its purpose, prerequisites, expected result and help when something goes wrong. Each chapter takes its steps and rules from the scenarios in `specs/`; nothing that the solution does not do.
3. **Pictures** for Power Apps: one walk per chapter and role in `docs/handbook/walks/` with skill ppp-app-walk, run in the session of that role so that each action shows its permissions. A line `<!-- walk: <name> -->` in the chapter takes the walk's numbered steps and pictures with frames; the clicks come from the walk alone, the chapter's text holds purpose, prerequisites, result and help (`ppp guide` warns about numbered steps beside a walk line). After a package, `ppp check` names the handbook walks whose screens changed since their pictures: run them again and rebuild the Word file. Where a walk is not possible, a tenant-step card asks for screenshots of named screens and states, saved to `docs/handbook/images/` and placed with a Markdown image line, its alt text the caption.
4. **Word**: `ppp guide docs/handbook/<name>.md` builds `docs/handbook/<name>.docx` (ppp-app-walk, section 6).
5. **Review**: the user hands the Word file to one or two end users; their remarks come back as material into `inputs/` and change the Markdown.
6. In-app help, if wanted: short texts per screen as a named formula or a help screen in the app, built like any other screen in a package.

Done when every task of each role has a chapter, every chapter with clicks has its walk run in that role's session, the Word file is built from the current Markdown and pictures, and every chapter was read by an end user.

## Training (`docs/training/`)
Only when the handbook is not enough: a short deck (see Presentations), a recorded walk (skill ppp-app-walk) or exercise sheet per user role, built on the handbook chapters.

## Presentations
Any deck ppp prepares (training, workshop, steering committee update) starts as its slide description, the template for the deck:
1. Write `docs/<area>/<name>.md` in the language of the deck: per slide one heading with number and title as a statement, below it the core message, the content points and the intended design (for example status per strand, timeline, comparison old → new). Done when every slide of the planned deck has its section and the user confirmed the outline.
2. Build in the corporate design with bi-ppt if it is installed (skill or agent), naming the slide description as its template. bi-ppt sets it as `"dokument"`, writes `<name>.pptx` and `<name>.spec.json` beside it and appends its own section with the built state; your text above stays. Without bi-ppt the slide description is the result, and the user builds the deck.
3. Later changes go through bi-ppt with the slide numbers from the slide description; bi-ppt changes only those slides.

## Six Sigma (`docs/six-sigma/`)
Only when the project plan provides it: one document per DMAIC phase (Define, Measure, Analyze, Improve, Control) with the content the plan asks for, fed from `specs/`, `decisions/` and measured data.

## Project material (`docs/project/`)
Workshop documents and results, team folder content, mails: keep them as they are; questionnaires for third parties come from ppp-clarify.
