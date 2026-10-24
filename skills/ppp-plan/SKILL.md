---
name: ppp-plan
description: Planning of development packages in ROADMAP.md after clarification. Use when the specs are settled and the work has to be cut into packages, or when the plan changes.
---

# Planning

The plan is `ROADMAP.md`: every package with number, goal and status (planned, active, done). It stays changeable.

## Cut the packages
1. **Size by mode**: small, usually one package; medium, a few; large, a rough plan with sections, detailed plans per section when it begins.
2. **Order by dependency**: lists and setup flow first (SharePoint), then the flows that write, then the app and the flows it calls, then reports. Scaffolds the user creates in the tenant (an empty flow with its trigger and one action per connector, an empty app, the solution) belong to the first package that needs them.
3. **One package = one import the user can test.** It ends with critical scenarios the user can check in a few minutes. A package that would need a long test is two packages.
4. Each line: number (`001`, `002`, …), short name, goal in one sentence, status "planned".

Done when every requirement of `specs/` belongs to a package and every package has a goal the user can test.

## Confirm and close
Show the plan in the chat and confirm it with one decision card. Then the stopping point of planning: overwrite `STATE.md` (next step: package 001 with ppp-package), commit, push, stopping-point card with a model recommendation for building.
