---
name: ppp-clarify
description: Clarification of requirements in card rounds until nothing is assumed silently; results in specs/ and decisions/. Use after intake, when new material or a new requirement arrives, or when a questionnaire for someone else is needed.
metadata:
  origin: "mattpocock/skills@49dd158 skills/productivity/grilling, skills/productivity/to-questionnaire, skills/engineering/domain-modeling (decision criteria); MIT; adapted, see THIRD_PARTY.md"
---

# Clarification

Clarify until you and the user share one understanding of the solution. Map it as a **design tree**: every decision branches into the decisions that hang off it.

## Depth by mode (`project.json`)
- **small**: settle what the build needs; name your assumptions on one card and let the user correct them.
- **medium**: settle what the first packages need; the rest iteratively. Probe the data: which lists, which volumes, which exports exist.
- **large**: current state, concept, specification with success criteria, no contradictions. If the project plan provides Six Sigma, follow its DMAIC phases and keep the documents in `docs/six-sigma/`.

## Rounds
1. **Read the material.** Everything in `inputs/` and the exports. A presentation with a slide description beside it (`<name>.md`, section from `<!-- bippt:folienbeschreibung`) is read through that description, the PPTX only for what it does not say. Facts are your job: look them up in files and exports, never ask the user for something you can find. Done when every input is read once and its facts are noted.
2. **Ask the frontier.** The frontier is every decision whose prerequisites are settled. Ask the whole frontier in one turn, one card per question, the recommended answer first, worded so that accepting it settles the question. A question that depends on another open question waits for a later round.
3. **Challenge.** Check each answer for contradictions with earlier answers, gaps and hidden assumptions, and advise with a recommendation. A requirement the user confirmed stays confirmed.
4. **Write down at once.** Each settled capability goes into `specs/<capability>.md` (`ppp new spec "<capability>"`): requirements as SHALL, scenarios as WHEN/THEN with concrete values. The scenarios are the base for the critical tests later.
5. **Repeat** with the new frontier. New material (a meeting, a transcript, an answer from a third party) goes to `inputs/` and starts a new round.

Done when the frontier is empty: every branch visited, every assumption confirmed on a card, every requirement in `specs/`.

## Decisions
Record a decision with `ppp new decision "<title>"` only when all three hold: hard to reverse, surprising without its context, and the result of a real trade-off. Context, decision, rejected alternatives, consequences.

## Questionnaire for a third party
When a decision needs knowledge only someone else has: ask the user who receives it and what is needed back, then write `docs/project/questionnaire-<slug>.md`: purpose, from and to, context in one paragraph, how to answer, questions grouped by theme, most important first, one idea per question with an answer line. The answers come back as material into `inputs/`.

## End
Stopping point of clarification: overwrite `STATE.md` (next step: prototype or planning), commit, push, stopping-point card.
