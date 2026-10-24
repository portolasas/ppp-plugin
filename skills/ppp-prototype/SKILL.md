---
name: ppp-prototype
description: Click mock-up of a planned app as one HTML file with JSON data, to collect feedback before building. Use when the user wants a prototype, a mock-up or a click dummy, or when clarification of a large project reaches the screens.
metadata:
  origin: "mattpocock/skills@49dd158 skills/engineering/prototype (UI branch); MIT; adapted, see THIRD_PARTY.md"
---

# Click mock-up

A prototype is **throwaway** and answers one question: does this app fit the process? It is no Power App and no base for the build.

## Build
1. State the question in one line at the top of `prototype/index.html`, e.g. "Can the shift lead plan a cleaning in under a minute?"
2. Screens as in the planned app (usually 5–6), navigation between them, realistic sample data in `prototype/data.json`. One HTML file with inline CSS and JavaScript that reads the JSON; it opens by double click, without a server (embed the JSON as a script block if the browser blocks local reads).
3. Brand design: if the skill bi-designer is installed, take colours, fonts and the logo rules from it; otherwise a neutral design.
4. Where the layout is open, build **variants** that differ in structure (navigation, information order, primary action), switchable from a small floating bar at the bottom. Three at most.
5. Surface the state: actions change the data visibly (a list grows, a status changes), so a non-developer understands the flow.

Done when every screen of the specs is reachable by clicks and the data covers the scenarios of `specs/`.

## Feedback
The user collects feedback with the people concerned. Their answers come as material into `inputs/`; settled changes go into `specs/` (ppp-clarify), then planning follows. The prototype stays in `prototype/` as a record of the design question; it is not maintained further.
