---
name: ppp-docs
description: Documents for people outside development - handbook, training, Six Sigma documents, questionnaires and project material in docs/. Use when a handbook, training, user guide, in-app help or DMAIC document is needed.
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
Only when the handbook is not enough: a short deck or exercise sheet per user role, built on the handbook chapters. For slides in the corporate design use the skill bi-ppt if it is installed.

## Six Sigma (`docs/six-sigma/`)
Only when the project plan provides it: one document per DMAIC phase (Define, Measure, Analyze, Improve, Control) with the content the plan asks for, fed from `specs/`, `decisions/` and measured data.

## Project material (`docs/project/`)
Workshop documents and results, team folder content, mails: keep them as they are; questionnaires for third parties come from ppp-clarify.
