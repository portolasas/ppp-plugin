---
name: ppp-diagnose
description: Diagnosis of errors in the tenant - a failing flow run, wrong data, an app that misbehaves, an import that is rejected. Use when the user reports something broken, failing, wrong or slow.
metadata:
  origin: "mattpocock/skills@49dd158 skills/engineering/diagnosing-bugs; MIT; adapted to exports, wdl_sim and cards, see THIRD_PARTY.md"
---

# Diagnosis

The tenant is out of reach, so the whole skill is getting a **feedback loop** that runs here: a local run that goes **red** on exactly the symptom the user reported.

## 1. What is already here, then evidence from the tenant
Start with what needs no tenant step: the error message the user reported, the definition in `solution/` (`ppp inventory <flow>`, search for the action and expression the message names), the list schema and earlier exports in `inputs/`. When message and definition explain the error, go straight to the feedback loop.

Ask for evidence only when a concrete question remains that only the tenant answers, and then for exports, not readings: the failed run (Run history › the run › Download, or Monitor export) for the inputs and outputs of an action, the affected list ("Export › CSV with schema") for data, the import message as text, a fresh solution export when the definition may differ from `solution/`. One tenant-step card names exactly what to export, where it goes (`exchange/`, or `inputs/` for data) and which question it answers. Personal data in these exports may be read.

Done when the symptom is captured: the error message, a wrong value or a failed action with its inputs, from the user's report or an export.

## 2. Feedback loop
Build one command that reproduces the symptom here, in this order:
1. `ppp verify --all` and `ppp canvas` when the error is a save or import error (InvalidTemplate, nesting, a missing reference).
2. A simulation with `wdl_sim` in `tests/` (`ppp run tests/<test>.py`): the exported flow, the trigger input and the list data of the run.
3. A reference calculation in Python for business logic, compared with the values from the export.

Done when the command has run and goes red on the user's symptom, not on a neighbouring one. Without such a command, say so, list what you tried and which export would close the gap.

## 3. Hypotheses
Write 3–5 ranked hypotheses, each falsifiable: "If X is the cause, changing Y makes the error disappear." Show them to the user before testing; they often know which one it is.

## 4. Test and fix
Change one thing at a time and rerun the loop. The fix becomes a package (ppp-package) or, if the user prefers a small fix by hand in the tenant, a card with the exact change plus a note in `STATE.md` under "Manual changes in the tenant". Keep the loop as a regression test in `tests/` when it is cheap to keep.

Done when the loop is green, the cause is named in the commit message, and the fix is either packed or noted.

If the cause was platform behaviour you did not know, propose a lesson (`ppp new lesson`).
