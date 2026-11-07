---
name: ppp-docs
description: Documents for people outside development - handbook, training, Six Sigma documents, questionnaires and project material in docs/. Use when a handbook, training, user guide, in-app help, DMAIC document or presentation is needed.
---

# Documents for people

The technical documentation is the project structure itself (`README.md`, `specs/`, the READMEs in `components/`, `decisions/`); keep it current per package. This skill covers what end users, trainers and the business read. These documents are in the language of the end users (`handbookLanguage` in `project.json`).

## Handbook (`docs/handbook/`)
0. **Format first**: before the first document for users is built, read `trainingFormat` in `project.json`. Missing: a decision card "Which documents should the users get?" with `word` (handbook, quick guide and exercise sheet per role in Word), `powerpoint` (handbook per role in Word; quick guide and exercises go into a training deck per role in PowerPoint, no Word quick guide or exercise sheet; needs the plugin bi-design) and `both` (all of it); recommend `both` when bi-design is installed and the users get a training, else `word`. Save the answer as `"trainingFormat"` in `project.json`; it decides what steps 4, 6 and 9 build. The handbook itself stays a Word file in every format.
1. **Outline with the users**: ask who reads it and for which tasks; one chapter per task, in the order the users work, not per screen. Each role gets its own handbook from the one Markdown file (step 4): it holds everything that role needs, also what other roles read too, and nothing it cannot do.
2. **Text in Markdown**: `docs/handbook/<name>.md` holds every text for the users: version, date, a short section "New in this version" with what changed for the users in their words, then purpose of the app, who may do what, an overview "I want to … → how", first start, terms, and per task:
   - **What for**: one or two sentences, the role below the heading (`<!-- for: … -->`), not in it;
   - the steps from the walk, one action per step, in the imperative, labels of the app in **bold** exactly as on the screen, at most about seven steps, otherwise split the task;
   - **Result**: what the user sees when it worked;
   - **If something goes wrong**: problem → what to do, right where it happens; one `> **Caution:** …` box only for a real risk, before the step it concerns.
   Each chapter takes its steps and rules from the scenarios in `specs/`; nothing that the solution does not do. Plain language: short sentences, positive wording ("Leave the field empty to …" rather than "not for none"), one term per thing as the app names it, no developer words: package numbers, test IDs, flow, job, list, recording, walk, evidence. A line `<!-- avoid: <words> -->` makes `ppp guide` warn where they appear, in the text and in the walks.
3. **Technical notes apart**: `docs/handbook/README.md`, in English, holds what the pictures prove and what not, recording limits, test data, solution versions and packages behind a version and the build commands. The user text never says what a picture did not save or prove.
4. **Roles, quick guide, exercises from the same Markdown**: a line `<!-- for: <role>, <role> -->` right below a heading limits that section and its subsections to these roles; elsewhere it opens a block up to `<!-- /for -->`. A section without it is for every role. `ppp guide <name>.md --role <role>` builds the handbook of that role; headings without content for it fall away. A chapter (`##`) with `<!-- kind: quick -->` belongs to the quick guide, one with `<!-- kind: exercises -->` to the exercise sheet; `--kind quick|exercises` builds those:
   - **Quick guide** per role, one page: purpose in one line, the three to six tasks of daily work with short steps (walk lines give their steps without pictures), status and colours as a small table, three frequent problems with the fix, contact, and where the full handbook is. `ppp guide` warns above about one page.
   - **Exercise sheet** per role: per exercise (`###`) a scenario of two sentences from daily work, the starting point (a marked test record without personal data), the task without the way, expected results as boxes to tick (`- [ ] …`), and after `<!-- solution -->` the way and frequent mistakes; `ppp guide` moves the solutions to a page of their own at the end. The last exercise removes the test data, as the project rules say.
5. **Pictures** for Power Apps: one walk per chapter and role in `docs/handbook/walks/` with skill ppp-app-walk, run in the session of that role so that each action shows its permissions.
   - A line `<!-- walk: <name> -->` in the chapter takes the walk's numbered steps and pictures with frames; the clicks come from the walk alone, the chapter's text holds what for, result and help (`ppp guide` warns about numbered steps beside a walk line).
   - Every click a reader has to make needs a `text` in the walk; `ppp guide` warns about more than three clicks in a row without one. A shot's `text` says what to check on that picture.
   - When a guide walk shows behaviour that contradicts `specs/` or looks like a defect, such as a click that drops a selection, a decision card comes before the chapter describes it: describe the current behaviour and note the fix for a package (recommended), or fix it first.
   - After a package, `ppp check` names the handbook walks whose screens changed since their pictures: run them again and rebuild the Word files.
   - Where a walk is not possible, a tenant-step card asks for screenshots of named screens and states, saved to `docs/handbook/images/` and placed with a Markdown image line, its alt text the caption.
   - `ppp guide --role` notes a walk of another role in a role's handbook: say in the text what this role sees differently.
6. **Word**: before you change the handbook's Markdown or build from it, read [references/guide.md](references/guide.md): the markers `ppp guide` reads, its layout rules, options, template and the Word specifics. `ppp guide docs/handbook/<name>.md [--role <role>] [--kind quick|exercises] --orientation portrait --word` builds the Word file in portrait, with the table of contents updated by Word. One file per role and kind, the build commands in `docs/handbook/README.md`. Then look at the pages in Word, or at a PDF of them for the page breaks: half-empty pages, a lead-in alone at a page end, a quick guide over one page.
7. **Review**: before the user hands the files on, read each one as its role: purpose first, every task findable from the overview, no developer words, `ppp guide` without warnings. Then the user gives each role's handbook to one end user of that role, best with a real task to do with it; their remarks come back as material into `inputs/` and change the Markdown.
8. In-app help, if wanted: short texts per screen as a named formula or a help screen in the app, built like any other screen in a package.
9. **Training deck** (`trainingFormat` `powerpoint` or `both`): `ppp guide docs/handbook/<name>.md --role <role> --kind deck` builds one compact deck per role in the corporate design of bi-design, from the same Markdown and pictures, so a change of the handbook reaches Word and slides alike. Before the first deck read [references/deck.md](references/deck.md): its parts, what a deck leaves out, the lines that shape a slide, and the check. Done for a deck when every slide was rendered and looked at, and every fix went into the Markdown or the deck lines, never into PowerPoint.

Done when every task of each role has a chapter, every chapter with clicks has its walk run in that role's session, the documents of `trainingFormat` (handbook of each role always; quick guide and exercise sheet in Word for `word` and `both`; training deck for `powerpoint` and `both`) are built from the current Markdown and pictures without warnings, every deck was rendered and looked at, and every role's handbook was read by an end user of that role.

## Training (`docs/training/`)
The exercise sheets of the handbook (step 4) or the training deck per role (step 9), as `trainingFormat` says, come first. Beyond them, when wanted: a recorded walk (skill ppp-app-walk) per user role, built on the handbook chapters.

## Presentations
Any deck ppp prepares (training, workshop, steering committee update) starts as its slide description, the template for the deck:
1. Write `docs/<area>/<name>.md` in the language of the deck: per slide one heading with number and title as a statement, below it the core message, the content points and the intended design (for example status per strand, timeline, comparison old → new). Done when every slide of the planned deck has its section and the user confirmed the outline.
2. Build in the corporate design with bi-ppt if it is installed (skill or agent), naming the slide description as its template. bi-ppt sets it as `"dokument"`, writes `<name>.pptx` and `<name>.spec.json` beside it and appends its own section with the built state; your text above stays. Without bi-ppt the slide description is the result, and the user builds the deck.
3. Later changes go through bi-ppt with the slide numbers from the slide description; bi-ppt changes only those slides.

## Six Sigma (`docs/six-sigma/`)
Only when the project plan provides it: one document per DMAIC phase (Define, Measure, Analyze, Improve, Control) with the content the plan asks for, fed from `specs/`, `decisions/` and measured data.

## Project material (`docs/project/`)
Workshop documents and results, team folder content, mails: keep them as they are; questionnaires for third parties come from ppp-clarify.
