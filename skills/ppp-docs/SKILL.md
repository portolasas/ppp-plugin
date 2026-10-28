---
name: ppp-docs
description: Documents for people outside development - handbook, training, Six Sigma documents, questionnaires and project material in docs/. Use when a handbook, training, user guide, in-app help, DMAIC document or presentation is needed.
---

# Documents for people

The technical documentation is the project structure itself (`README.md`, `specs/`, the READMEs in `components/`, `decisions/`); keep it current per package. This skill covers what end users, trainers and the business read. These documents are in the language of the end users (`handbookLanguage` in `project.json`).

## Handbook (`docs/handbook/`)
1. **Outline with the users**: ask who reads it and for which tasks; one chapter per task, in the order the users work, not per screen.
2. **Content from the specs**: each chapter takes its steps and rules from the scenarios in `specs/`; nothing that the solution does not do.
3. **Pictures** for Power Apps: a tenant-step card asks for screenshots of named screens and states, saved to `docs/handbook/images/`. Mark highlights in the text, not in the picture.
4. **Review**: the user hands the draft to one or two end users; their remarks come back as material into `inputs/`.
5. In-app help, if wanted: short texts per screen as a named formula or a help screen in the app, built like any other screen in a package.

Done when every task of the users has a chapter and every chapter was read by an end user.

## Training (`docs/training/`)
Only when the handbook is not enough: a short deck (see Presentations) or exercise sheet per user role, built on the handbook chapters.

## Presentations
Any deck ppp prepares (training, workshop, steering committee update) starts as its slide description, the template for the deck:
1. Write `docs/<area>/<name>.md` in the language of the deck: per slide one heading with number and title as a statement, below it the core message, the content points and the intended design (for example status per strand, timeline, comparison old → new). Done when every slide of the planned deck has its section and the user confirmed the outline.
2. Build in the corporate design with bi-ppt if it is installed (skill or agent), naming the slide description as its template. bi-ppt sets it as `"dokument"`, writes `<name>.pptx` and `<name>.spec.json` beside it and appends its own section with the built state; your text above stays. Without bi-ppt the slide description is the result, and the user builds the deck.
3. Later changes go through bi-ppt with the slide numbers from the slide description; bi-ppt changes only those slides.

## Six Sigma (`docs/six-sigma/`)
Only when the project plan provides it: one document per DMAIC phase (Define, Measure, Analyze, Improve, Control) with the content the plan asks for, fed from `specs/`, `decisions/` and measured data.

## Project material (`docs/project/`)
Workshop documents and results, team folder content, mails: keep them as they are; questionnaires for third parties come from ppp-clarify.
